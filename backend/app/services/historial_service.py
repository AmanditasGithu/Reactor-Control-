"""US-023: registro atómico e idempotente de resultados de una partida.

El servidor del juego es la única fuente autorizada de resultados. Todas las
modificaciones se confirman en una única transacción SQLAlchemy.
"""
from hashlib import sha256
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import Jugador, Participacion, Partida, Record, ResultadoRecibido
from app.schemas import FinalizacionEntrante


def _guardar_finalizacion(db: Session, entrada: FinalizacionEntrante) -> tuple[int, bool]:
    huella = sha256(entrada.model_dump_json(exclude_none=True).encode("utf-8")).hexdigest()
    # Se comprueba antes de modificar cualquier contador.
    with db.begin():
        anterior = db.get(ResultadoRecibido, entrada.id_externo)
        if anterior is not None:
            if anterior.huella != huella:
                raise HTTPException(409, "Ese identificador ya tiene otro resultado registrado")
            return anterior.partida_id, True

        ids = [r.id_jugador for r in entrada.resultados_finales]
        jugadores = {
            j.id: j for j in db.scalars(select(Jugador).where(Jugador.id.in_(ids)))
        }
        faltantes = sorted(set(ids) - jugadores.keys())
        if faltantes:
            raise HTTPException(422, f"Jugadores sin cuenta registrada: {faltantes}")

        partida = Partida(
            estado="finalizada", escenario=entrada.escenario,
            puntuacion_objetivo=entrada.puntuacion_objetivo,
            duracion_segundos=entrada.duracion_segundos,
            fecha_inicio=entrada.inicio_utc,
            fecha_fin=entrada.fin_utc,
            ganador_id=entrada.resultados_finales[0].id_jugador,
        )
        db.add(partida)
        db.flush()  # obtener id real en PostgreSQL, sin confirmar todavía

        for posicion, resultado in enumerate(entrada.resultados_finales, 1):
            jugador = jugadores[resultado.id_jugador]
            db.add(Participacion(
                partida_id=partida.id, jugador_id=jugador.id,
                puntos=resultado.puntos, posicion=posicion,
            ))
            jugador.puntos_totales += resultado.puntos
            jugador.partidas_jugadas += 1
            if posicion == 1:
                jugador.victorias += 1

            record = db.scalar(select(Record).where(
                Record.jugador_id == jugador.id,
                Record.tipo == "mayor_puntuacion",
            ))
            if record is None:
                db.add(Record(
                    jugador_id=jugador.id, partida_id=partida.id,
                    tipo="mayor_puntuacion", valor=resultado.puntos,
                ))
            elif resultado.puntos > record.valor:
                record.valor = resultado.puntos
                record.partida_id = partida.id
                record.fecha = datetime.now(timezone.utc)

        db.add(ResultadoRecibido(
            id_externo=entrada.id_externo,
            partida_id=partida.id, huella=huella, motivo_fin=entrada.motivo_fin,
        ))
        partida_id = partida.id
    return partida_id, False


def guardar_finalizacion(db: Session, entrada: FinalizacionEntrante) -> tuple[int, bool]:
    """También resuelve reenvíos simultáneos en distintos workers/instancias.

    El índice único de resultados_recibidos evita la doble contabilidad; una
    carrera de escritura se reinterpreta como reenvío idempotente.
    """
    try:
        return _guardar_finalizacion(db, entrada)
    except IntegrityError:
        db.rollback()
        anterior = db.get(ResultadoRecibido, entrada.id_externo)
        if anterior is None:
            raise  # Otro problema de integridad, no esconderlo.
        huella = sha256(entrada.model_dump_json(exclude_none=True).encode("utf-8")).hexdigest()
        if anterior.huella != huella:
            raise HTTPException(409, "Ese identificador ya tiene otro resultado registrado")
        return anterior.partida_id, True
