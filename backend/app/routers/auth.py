"""Rutas de la API para las cuentas de jugador."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.jugador_repository import JugadorRepository
from app.schemas import JugadorResponse, RegistroRequest
from app.services.auth_service import (
    AuthService,
    CorreoYaRegistrado,
    NombreUsuarioYaRegistrado,
)

router = APIRouter(prefix="/api/auth", tags=["Cuentas"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(JugadorRepository(db))


@router.post("/registro", response_model=JugadorResponse, status_code=status.HTTP_201_CREATED)
def registrar(datos: RegistroRequest, servicio: AuthService = Depends(get_auth_service)):
    """US-001: crea una cuenta con nombre de usuario, correo y contraseña."""
    try:
        return servicio.registrar(datos)
    except CorreoYaRegistrado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    except NombreUsuarioYaRegistrado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese nombre de usuario ya está en uso")