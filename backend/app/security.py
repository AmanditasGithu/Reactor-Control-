"""Cifrado de contraseñas (RNF-04) y tokens de sesión (RNF-07)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import JWT_ALGORITMO, JWT_MINUTOS_EXPIRACION, JWT_SECRET


def cifrar_contrasena(contrasena: str) -> str:
    """Devuelve la contraseña cifrada con bcrypt, lista para guardar."""
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    """Revisa si una contraseña coincide con la versión cifrada guardada."""
    return bcrypt.checkpw(contrasena.encode("utf-8"), contrasena_hash.encode("utf-8"))


def crear_token(jugador_id: int) -> str:
    """Crea el token de sesión que recibe el jugador al iniciar sesión (RNF-07)."""
    vence = datetime.now(timezone.utc) + timedelta(minutes=JWT_MINUTOS_EXPIRACION)
    datos = {"sub": str(jugador_id), "exp": vence}
    return jwt.encode(datos, JWT_SECRET, algorithm=JWT_ALGORITMO)


def leer_token(token: str) -> int | None:
    """Devuelve el id del jugador dueño del token, o None si es falso o ya venció."""
    try:
        datos = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITMO])
        return int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def generar_codigo() -> str:
    """Crea un código al azar de 6 números para recuperar la contraseña (US-005)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def cifrar_codigo(codigo: str) -> str:
    """Cifra el código antes de guardarlo, igual que se hace con las contraseñas."""
    return hashlib.sha256(codigo.encode("utf-8")).hexdigest()
