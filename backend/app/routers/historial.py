"""US-023: envío autorizado desde el servidor de juego y consultas por usuario."""
import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import get_jugador_actual
from app.models import Jugador, Participacion, Partida, Record, ResultadoRecibido
from app.schemas import (
    DetallePartidaResponse, FinalizacionEntrante, HistorialFilaResponse,
    HistorialPaginadoResponse, RecordResponse, ResultadoGuardadoResponse,
    ResultadoParticipanteResponse,
)
from app.services.historial_service import guardar_finalizacion

router = APIRouter(prefix="/api", tags=["Historial y récords - US-023"])


@router.post("/interno/resultados", response_model=ResultadoGuardadoResponse)
def registrar_finalizacion(
    entrada: FinalizacionEntrante,
    x_reactor_servicio: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Solo el servidor del juego conoce la clave compartida (nunca el frontend)."""
    secreto = os.getenv("REACTOR_RESULTADOS_TOKEN", "")
    if not secreto:
        raise HTTPException(503, "Recepción de resultados sin configurar")
    if not x_reactor_servicio or not hmac.compare_digest(x_reactor_servicio, secreto):
        raise HTTPException(403, "Servicio no autorizado")
    partida_id, duplicado = guardar_finalizacion(db, entrada)
    return ResultadoGuardadoResponse(partida_id=partida_id, duplicado=duplicado)


@router.get("/historial", response_model=HistorialPaginadoResponse)
def consultar_historial(
    limite: int = Query(8, ge=1, le=50),
    offset: int = Query(0, ge=0),
    jugador: Jugador = Depends(get_jugador_actual),
    db: Session = Depends(get_db),
):
    filtro = (Participacion.jugador_id == jugador.id, Partida.estado == "finalizada")
    total = db.scalar(select(func.count()).select_from(Participacion)
                      .join(Partida, Participacion.partida_id == Partida.id)
                      .where(*filtro)) or 0
    datos = db.execute(
        select(Participacion, Partida, ResultadoRecibido.motivo_fin)
        .join(Partida, Participacion.partida_id == Partida.id)
        .outerjoin(ResultadoRecibido, ResultadoRecibido.partida_id == Partida.id)
        .where(*filtro)
        .order_by(Partida.fecha_fin.desc(), Partida.id.desc())
        .offset(offset).limit(limite)
    ).all()
    filas = [HistorialFilaResponse(
        partida_id=partida.id, escenario=partida.escenario,
        fecha=partida.fecha_fin or partida.fecha_inicio,
        puntos=participacion.puntos, posicion=participacion.posicion,
        ganador_id=partida.ganador_id, motivo_fin=motivo,
    ) for participacion, partida, motivo in datos]
    return HistorialPaginadoResponse(total=total, limite=limite, offset=offset, partidas=filas)


@router.get("/records", response_model=list[RecordResponse])
def consultar_records(
    jugador: Jugador = Depends(get_jugador_actual),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(Record)
                           .where(Record.jugador_id == jugador.id)
                           .order_by(Record.tipo)))


@router.get("/historial/{id_partida}", response_model=DetallePartidaResponse)
def detalle_partida(
    id_partida: int,
    jugador: Jugador = Depends(get_jugador_actual),
    db: Session = Depends(get_db),
):
    permitido = db.scalar(select(Participacion.id).join(Partida)
                          .where(Participacion.partida_id == id_partida,
                                 Participacion.jugador_id == jugador.id,
                                 Partida.estado == "finalizada"))
    if permitido is None:
        # No revelar la existencia de partidas de otros usuarios.
        raise HTTPException(404, "Partida no encontrada en tu historial")
    partida = db.get(Partida, id_partida)
    motivo = db.scalar(select(ResultadoRecibido.motivo_fin)
                       .where(ResultadoRecibido.partida_id == id_partida))
    datos = db.execute(select(Participacion, Jugador)
                       .join(Jugador, Participacion.jugador_id == Jugador.id)
                       .where(Participacion.partida_id == id_partida)
                       .order_by(Participacion.posicion)).all()
    return DetallePartidaResponse(
        partida_id=partida.id, escenario=partida.escenario,
        fecha_inicio=partida.fecha_inicio, fecha_fin=partida.fecha_fin,
        duracion_segundos=partida.duracion_segundos,
        puntuacion_objetivo=partida.puntuacion_objetivo,
        motivo_fin=motivo, ganador_id=partida.ganador_id,
        participantes=[ResultadoParticipanteResponse(
            id_jugador=j.id, nombre_usuario=j.nombre_usuario,
            puntos=p.puntos, posicion=p.posicion,
        ) for p, j in datos],
    )
