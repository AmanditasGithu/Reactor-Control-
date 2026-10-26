"""Formato de los datos que entran y salen de la API.

Pydantic revisa automáticamente que los datos tengan el formato correcto.
Si algo no cumple, la API responde con error 422 sin llegar a la base de datos.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegistroRequest(BaseModel):
    """Datos que envía el jugador para crear su cuenta (US-001)."""

    nombre_usuario: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9_]+$")
    correo: EmailStr
    contrasena: str = Field(min_length=8)

    @field_validator("correo")
    @classmethod
    def correo_en_minusculas(cls, valor: str) -> str:
        # Ana@Correo.com y ana@correo.com son el mismo correo (RN-01)
        return valor.lower()

    @field_validator("contrasena")
    @classmethod
    def contrasena_no_muy_larga(cls, valor: str) -> str:
        # bcrypt solo acepta hasta 72 bytes
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga (máximo 72 caracteres)")
        return valor


class JugadorResponse(BaseModel):
    """Datos del jugador que la API devuelve. Nunca incluye la contraseña."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre_usuario: str
    correo: str
    correo_verificado: bool
    fecha_registro: datetime


class LoginRequest(BaseModel):
    """Datos para iniciar sesión (US-004). Se puede entrar con correo o con nombre de usuario."""

    usuario_o_correo: str = Field(min_length=1)
    contrasena: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Respuesta del login: el token que demuestra que el jugador inició sesión."""

    access_token: str
    token_type: str = "bearer"
    jugador: JugadorResponse


class FilaRanking(BaseModel):
    """Una fila del ranking global (US-022)."""

    posicion: int
    nombre_usuario: str
    puntos_totales: int
    victorias: int
    partidas_jugadas: int


class PartidaEnHistorial(BaseModel):
    """Una partida jugada, vista desde el perfil del jugador."""

    partida_id: int
    escenario: str
    fecha: datetime | None
    puntos: int
    posicion: int | None


class RecordResponse(BaseModel):
    """Un récord del jugador, por ejemplo su mayor puntuación."""

    model_config = ConfigDict(from_attributes=True)

    tipo: str
    valor: int
    fecha: datetime


class PerfilResponse(BaseModel):
    """Perfil completo del jugador (US-006)."""

    nombre_usuario: str
    correo: str
    fecha_registro: datetime
    puntos_totales: int
    victorias: int
    partidas_jugadas: int
    posicion_ranking: int
    historial: list[PartidaEnHistorial]
    records: list[RecordResponse]


class SolicitarRecuperacionRequest(BaseModel):
    """US-005, paso 1: el jugador escribe su correo para recibir un código."""

    correo: EmailStr

    @field_validator("correo")
    @classmethod
    def correo_en_minusculas(cls, valor: str) -> str:
        return valor.lower()


class RestablecerContrasenaRequest(BaseModel):
    """US-005, paso 2: el jugador escribe el código y su contraseña nueva."""

    correo: EmailStr
    codigo: str = Field(pattern=r"^\d{6}$")
    contrasena_nueva: str = Field(min_length=8)

    @field_validator("correo")
    @classmethod
    def correo_en_minusculas(cls, valor: str) -> str:
        return valor.lower()

    @field_validator("contrasena_nueva")
    @classmethod
    def contrasena_no_muy_larga(cls, valor: str) -> str:
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga (máximo 72 caracteres)")
        return valor


class MensajeResponse(BaseModel):
    """Respuesta que solo trae un mensaje para mostrar al jugador."""

    mensaje: str


class VerificarCorreoRequest(BaseModel):
    """US-003: el jugador escribe su correo y el código que le llegó."""

    correo: EmailStr
    codigo: str = Field(pattern=r"^\d{6}$")

    @field_validator("correo")
    @classmethod
    def correo_en_minusculas(cls, valor: str) -> str:
        return valor.lower()


class ReenviarCodigoRequest(BaseModel):
    """US-003: pedir otro código de verificación."""

    correo: EmailStr

    @field_validator("correo")
    @classmethod
    def correo_en_minusculas(cls, valor: str) -> str:
        return valor.lower()
