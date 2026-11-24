"""Patrón Repository: acceso a `cuentas_sociales` e `inicios_sociales` (US-002)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CuentaSocial, InicioSocial


class SocialRepository:
    """Guarda y busca las cuentas de Google/GitHub y los inicios de sesión en proceso."""

    def __init__(self, db: Session):
        self.db = db

    def buscar_cuenta(self, proveedor: str, proveedor_id: str) -> CuentaSocial | None:
        return self.db.scalar(
            select(CuentaSocial).where(
                CuentaSocial.proveedor == proveedor, CuentaSocial.proveedor_id == proveedor_id
            )
        )

    def buscar_inicio_por_state(self, state_hash: str) -> InicioSocial | None:
        return self.db.scalar(select(InicioSocial).where(InicioSocial.state_hash == state_hash))

    def buscar_inicio_por_espera(self, espera_hash: str) -> InicioSocial | None:
        return self.db.scalar(select(InicioSocial).where(InicioSocial.espera_hash == espera_hash))

    def agregar(self, objeto) -> None:
        self.db.add(objeto)

    def guardar_cambios(self) -> None:
        self.db.commit()
