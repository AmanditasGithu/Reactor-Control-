"""Patrón Repository: acceso a la tabla `codigos_verificacion` (US-003)."""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import CodigoVerificacion


class VerificacionRepository:
    """Guarda y busca los códigos para verificar el correo."""

    def __init__(self, db: Session):
        self.db = db

    def anular_codigos(self, jugador_id: int) -> None:
        """Marca como usados los códigos anteriores: solo sirve el más nuevo."""
        self.db.execute(
            update(CodigoVerificacion)
            .where(CodigoVerificacion.jugador_id == jugador_id, CodigoVerificacion.usado.is_(False))
            .values(usado=True)
        )

    def codigo_vigente(self, jugador_id: int) -> CodigoVerificacion | None:
        """El último código sin usar del jugador (puede estar vencido; eso lo revisa el servicio)."""
        return self.db.scalar(
            select(CodigoVerificacion)
            .where(CodigoVerificacion.jugador_id == jugador_id, CodigoVerificacion.usado.is_(False))
            .order_by(CodigoVerificacion.id.desc())
        )

    def agregar(self, objeto) -> None:
        self.db.add(objeto)

    def guardar_cambios(self) -> None:
        self.db.commit()
