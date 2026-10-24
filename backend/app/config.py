"""Configuración del backend.

Los valores se leen de variables de entorno. Si no existen, se usan
valores por defecto pensados para desarrollo local con docker-compose.
"""
import os

# Dirección de la base de datos. En docker-compose apunta al contenedor "db".
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://reactor:reactor@localhost:5432/reactor",
)

# Tokens de sesión (US-004, RNF-07).
# La clave secreta de desarrollo NO sirve para producción: en la nube se cambia
# con la variable de entorno JWT_SECRET.
JWT_SECRET = os.getenv("JWT_SECRET", "clave-solo-para-desarrollo-cambiar-en-produccion")
JWT_ALGORITMO = "HS256"
JWT_MINUTOS_EXPIRACION = int(os.getenv("JWT_MINUTOS_EXPIRACION", "60"))