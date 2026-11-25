"""Punto de entrada del backend de Control del Reactor."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import crear_tablas
from app.routers import auth, estadisticas, historial, social


@asynccontextmanager
async def lifespan(app: FastAPI):
    crear_tablas()  # al arrancar, crea las tablas si no existen
    yield


app = FastAPI(title="Control del Reactor - API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(social.router)  # US-002: Google y GitHub
app.include_router(estadisticas.router)
app.include_router(historial.router)

# US-024: versión web para celular. Se abre en el navegador: http://<ip-de-la-compu>:8000/movil
app.mount("/movil", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="movil")


@app.get("/", include_in_schema=False)
def inicio():
    """La dirección principal lleva a la versión para celular."""
    return RedirectResponse("/movil/")


@app.get("/health")
def health():
    """Sirve para comprobar que el backend está corriendo."""
    return {"estado": "ok"}
