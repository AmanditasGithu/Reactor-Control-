"""Patrón Repository: acceso a la tabla `codigos_recuperacion` (US-005)."""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import CodigoRecuperacion


class RecuperacionRepository:
    """Guarda y busca los códigos para recuperar la contraseña."""

    def __init__(self, db: Session):
        self.db = db

    def anular_codigos(self, jugador_id: int) -> None:
        """Marca como usados los códigos anteriores: solo sirve el más nuevo."""
        self.db.execute(
            update(CodigoRecuperacion)
            .where(CodigoRecuperacion.jugador_id == jugador_id, CodigoRecuperacion.usado.is_(False))
            .values(usado=True)
        )

    def codigo_vigente(self, jugador_id: int) -> CodigoRecuperacion | None:
        """El último código sin usar del jugador (puede estar vencido; eso lo revisa el servicio)."""
        return self.db.scalar(
            select(CodigoRecuperacion)
            .where(CodigoRecuperacion.jugador_id == jugador_id, CodigoRecuperacion.usado.is_(False))
            .order_by(CodigoRecuperacion.id.desc())
        )

    def agregar(self, objeto) -> None:
        self.db.add(objeto)

    def guardar_cambios(self) -> None:
        self.db.commit()
