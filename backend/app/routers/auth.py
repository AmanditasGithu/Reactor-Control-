"""Rutas de la API para las cuentas de jugador."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import get_jugador_actual
from app.models import Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.schemas import JugadorResponse, LoginRequest, RegistroRequest, TokenResponse
from app.services.auth_service import (
    AuthService,
    CorreoYaRegistrado,
    CredencialesInvalidas,
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


@router.post("/login", response_model=TokenResponse)
def iniciar_sesion(datos: LoginRequest, servicio: AuthService = Depends(get_auth_service)):
    """US-004: inicia sesión con correo o nombre de usuario y contraseña."""
    try:
        jugador, token = servicio.iniciar_sesion(datos)
    except CredencialesInvalidas:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario, correo o contraseña incorrectos"
        )
    return TokenResponse(access_token=token, jugador=JugadorResponse.model_validate(jugador))


@router.get("/yo", response_model=JugadorResponse)
def quien_soy(jugador: Jugador = Depends(get_jugador_actual)):
    """Devuelve el jugador que tiene la sesión iniciada. Requiere el token del login."""
    return jugador