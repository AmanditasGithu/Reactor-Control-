"""Patrón Repository: todo el acceso a la tabla `jugadores` pasa por aquí."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Jugador


class JugadorRepository:
    """Guarda y busca jugadores en la base de datos."""

    def __init__(self, db: Session):
        self.db = db

    def buscar_por_correo(self, correo: str) -> Jugador | None:
        return self.db.scalar(select(Jugador).where(Jugador.correo == correo))

    def buscar_por_nombre_usuario(self, nombre_usuario: str) -> Jugador | None:
        return self.db.scalar(select(Jugador).where(Jugador.nombre_usuario == nombre_usuario))

    def guardar(self, jugador: Jugador) -> Jugador:
        self.db.add(jugador)
        self.db.commit()
        self.db.refresh(jugador)  # trae el id y la fecha que puso la base de datos
        return jugador

    def buscar_por_id(self, jugador_id: int) -> Jugador | None:
        return self.db.get(Jugador, jugador_id)