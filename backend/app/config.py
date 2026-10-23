"""Configuración del backend. #guarda la dirección de la base de datos para no repetirla en cada archivo.

Los valores se leen de variables de entorno. Si no existen, se usan
valores por defecto pensados para desarrollo local con docker-compose.
"""
import os

# Dirección de la base de datos. En docker-compose apunta al contenedor "db".
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://reactor:reactor@localhost:5432/reactor",
)