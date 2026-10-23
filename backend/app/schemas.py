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