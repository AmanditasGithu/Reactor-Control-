"""Punto de entrada del backend de Control del Reactor."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import crear_tablas
from app.routers import auth, estadisticas


@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_tablas()  # al arrancar, crea las tablas si no existen
    yield


app = FastAPI(title="Control del Reactor - API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(estadisticas.router)


@app.get("/health")
def health():
    """Sirve para comprobar que el backend está corriendo."""
    return {"estado": "ok"}
