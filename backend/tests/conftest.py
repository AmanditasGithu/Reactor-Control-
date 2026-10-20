"""Configuración común de las pruebas.

Las pruebas usan SQLite en memoria para no necesitar PostgreSQL ni Docker:
así corren igual en cualquier compu y en el pipeline de CI.
"""
import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, crear_tablas, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def base_limpia():
    """Cada prueba empieza con las tablas vacías."""
    crear_tablas()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture
def client():
    return TestClient(app)