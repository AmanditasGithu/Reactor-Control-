"""Rutas del perfil del jugador (US-006) y del ranking global (US-022)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import get_jugador_actual
from app.models import Jugador
from app.repositories.estadisticas_repository import EstadisticasRepository
from app.schemas import FilaRanking, PerfilResponse
from app.services.estadisticas_service import EstadisticasService

router = APIRouter(prefix="/api", tags=["Perfil y ranking"])


def get_estadisticas_service(db: Session = Depends(get_db)) -> EstadisticasService:
    return EstadisticasService(EstadisticasRepository(db))


@router.get("/perfil", response_model=PerfilResponse)
def mi_perfil(
    jugador: Jugador = Depends(get_jugador_actual),
    servicio: EstadisticasService = Depends(get_estadisticas_service),
):
    """US-006: perfil del jugador con sesión iniciada. Requiere el token del login."""
    return servicio.perfil(jugador)


@router.get("/ranking", response_model=list[FilaRanking])
def ranking_global(
    limite: int = Query(10, ge=1, le=100),
    servicio: EstadisticasService = Depends(get_estadisticas_service),
):
    """US-022: top de jugadores por puntos acumulados (10 por defecto)."""
    return servicio.ranking(limite)
