"""Piezas que las rutas piden con Depends(...).

`get_jugador_actual` sirve para cualquier ruta que necesite un jugador con sesión
iniciada, por ejemplo unirse a una partida (US-007).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.security import leer_token

esquema_bearer = HTTPBearer(auto_error=False)


def get_jugador_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Jugador:
    """Devuelve el jugador dueño del token. Responde 401 si no hay token o no es válido."""
    no_autorizado = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Sesión no válida o vencida. Iniciá sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None:
        raise no_autorizado

    jugador_id = leer_token(credenciales.credentials)
    if jugador_id is None:
        raise no_autorizado

    jugador = JugadorRepository(db).buscar_por_id(jugador_id)
    if jugador is None:
        raise no_autorizado
    return jugador"""Piezas que las rutas piden con Depends(...).

`get_jugador_actual` sirve para cualquier ruta que necesite un jugador con sesión
iniciada, por ejemplo unirse a una partida (US-007).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.security import leer_token

esquema_bearer = HTTPBearer(auto_error=False)


def get_jugador_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Jugador:
    """Devuelve el jugador dueño del token. Responde 401 si no hay token o no es válido."""
    no_autorizado = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Sesión no válida o vencida. Iniciá sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciales is None:
        raise no_autorizado

    jugador_id = leer_token(credenciales.credentials)
    if jugador_id is None:
        raise no_autorizado

    jugador = JugadorRepository(db).buscar_por_id(jugador_id)
    if jugador is None:
        raise no_autorizado
    return jugador