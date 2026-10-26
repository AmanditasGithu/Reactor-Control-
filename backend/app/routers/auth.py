"""Rutas de la API para las cuentas de jugador."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencias import get_jugador_actual
from app.models import Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.recuperacion_repository import RecuperacionRepository
from app.repositories.verificacion_repository import VerificacionRepository
from app.schemas import (
    JugadorResponse,
    LoginRequest,
    MensajeResponse,
    ReenviarCodigoRequest,
    RegistroRequest,
    RestablecerContrasenaRequest,
    SolicitarRecuperacionRequest,
    TokenResponse,
    VerificarCorreoRequest,
)
from app.services.auth_service import (
    AuthService,
    CorreoNoVerificado,
    CorreoYaRegistrado,
    CredencialesInvalidas,
    NombreUsuarioYaRegistrado,
)
from app.services.recuperacion_service import CodigoInvalido, RecuperacionService
from app.services.verificacion_service import CodigoVerificacionInvalido, VerificacionService

router = APIRouter(prefix="/api/auth", tags=["Cuentas"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(JugadorRepository(db))


def get_verificacion_service(db: Session = Depends(get_db)) -> VerificacionService:
    return VerificacionService(JugadorRepository(db), VerificacionRepository(db))


def get_recuperacion_service(db: Session = Depends(get_db)) -> RecuperacionService:
    return RecuperacionService(JugadorRepository(db), RecuperacionRepository(db))


@router.post("/registro", response_model=JugadorResponse, status_code=status.HTTP_201_CREATED)
def registrar(
    datos: RegistroRequest,
    servicio: AuthService = Depends(get_auth_service),
    verificacion: VerificacionService = Depends(get_verificacion_service),
):
    """US-001: crea una cuenta con nombre de usuario, correo y contraseña.
    US-003: además envía un código para verificar el correo."""
    try:
        jugador = servicio.registrar(datos)
    except CorreoYaRegistrado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya está registrado")
    except NombreUsuarioYaRegistrado:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese nombre de usuario ya está en uso")
    verificacion.enviar_codigo(jugador)
    return jugador


@router.post("/login", response_model=TokenResponse)
def iniciar_sesion(datos: LoginRequest, servicio: AuthService = Depends(get_auth_service)):
    """US-004: inicia sesión con correo o nombre de usuario y contraseña."""
    try:
        jugador, token = servicio.iniciar_sesion(datos)
    except CredencialesInvalidas:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Usuario, correo o contraseña incorrectos"
        )
    except CorreoNoVerificado:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Verificá tu correo antes de iniciar sesión"
        )
    return TokenResponse(access_token=token, jugador=JugadorResponse.model_validate(jugador))


@router.get("/yo", response_model=JugadorResponse)
def quien_soy(jugador: Jugador = Depends(get_jugador_actual)):
    """Devuelve el jugador que tiene la sesión iniciada. Requiere el token del login."""
    return jugador


@router.post("/recuperar/solicitar", response_model=MensajeResponse)
def solicitar_codigo(
    datos: SolicitarRecuperacionRequest,
    servicio: RecuperacionService = Depends(get_recuperacion_service),
):
    """US-005 paso 1: envía un código al correo. Responde lo mismo aunque el correo no exista."""
    servicio.solicitar_codigo(datos.correo)
    return MensajeResponse(mensaje="Si el correo está registrado, te enviamos un código")


@router.post("/recuperar/restablecer", response_model=MensajeResponse)
def restablecer_contrasena(
    datos: RestablecerContrasenaRequest,
    servicio: RecuperacionService = Depends(get_recuperacion_service),
):
    """US-005 paso 2: cambia la contraseña usando el código recibido."""
    try:
        servicio.restablecer(datos)
    except CodigoInvalido:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El código es incorrecto o ya venció")
    return MensajeResponse(mensaje="Contraseña cambiada. Ya podés iniciar sesión")


@router.post("/verificar", response_model=MensajeResponse)
def verificar_correo(
    datos: VerificarCorreoRequest,
    servicio: VerificacionService = Depends(get_verificacion_service),
):
    """US-003: marca el correo como verificado usando el código recibido."""
    try:
        servicio.verificar(datos)
    except CodigoVerificacionInvalido:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El código es incorrecto o ya venció")
    return MensajeResponse(mensaje="¡Correo verificado!")


@router.post("/verificar/reenviar", response_model=MensajeResponse)
def reenviar_codigo(
    datos: ReenviarCodigoRequest,
    servicio: VerificacionService = Depends(get_verificacion_service),
):
    """US-003: envía otro código. Responde lo mismo aunque el correo no exista."""
    servicio.reenviar(datos.correo)
    return MensajeResponse(mensaje="Si el correo está registrado y sin verificar, te enviamos un código")
