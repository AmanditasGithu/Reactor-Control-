"""Consultas de puntos, ranking, historial y récords."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Jugador, Participacion, Partida, Record


class EstadisticasRepository:
    def __init__(self, db: Session):
        self.db = db

    def ranking(self, limite: int) -> list[Jugador]:
        """Jugadores ordenados por puntos; si empatan, por victorias y después por nombre."""
        consulta = (
            select(Jugador)
            .order_by(
                Jugador.puntos_totales.desc(),
                Jugador.victorias.desc(),
                Jugador.nombre_usuario,
            )
            .limit(limite)
        )
        return list(self.db.scalars(consulta))

    def posicion(self, jugador: Jugador) -> int:
        """Lugar del jugador en el ranking: 1 + cuántos tienen más puntos (empates comparten lugar)."""
        con_mas_puntos = self.db.scalar(
            select(func.count()).select_from(Jugador).where(Jugador.puntos_totales > jugador.puntos_totales)
        )
        return con_mas_puntos + 1

    def historial(self, jugador_id: int, limite: int) -> list[tuple[Participacion, Partida]]:
        """Últimas partidas del jugador, de la más reciente a la más vieja."""
        consulta = (
            select(Participacion, Partida)
            .join(Partida, Participacion.partida_id == Partida.id)
            .where(Participacion.jugador_id == jugador_id)
            .order_by(Partida.id.desc())
            .limit(limite)
        )
        return [(fila[0], fila[1]) for fila in self.db.execute(consulta)]

    def records(self, jugador_id: int) -> list[Record]:
        consulta = select(Record).where(Record.jugador_id == jugador_id).order_by(Record.tipo)
        return list(self.db.scalars(consulta))

    def buscar_jugador(self, jugador_id: int) -> Jugador | None:
        return self.db.get(Jugador, jugador_id)

    def buscar_participacion(self, partida_id: int, jugador_id: int) -> Participacion | None:
        return self.db.scalar(
            select(Participacion).where(
                Participacion.partida_id == partida_id, Participacion.jugador_id == jugador_id
            )
        )

    def buscar_record(self, jugador_id: int, tipo: str) -> Record | None:
        return self.db.scalar(select(Record).where(Record.jugador_id == jugador_id, Record.tipo == tipo))

    def guardar_todo(self, objetos: list) -> None:
        self.db.add_all(objetos)
        self.db.commit()
