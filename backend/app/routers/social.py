"""Rutas del login con redes sociales: Google y GitHub (US-002).

El paso a paso completo está explicado en app/services/social_service.py.
"""
from html import escape

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.social_repository import SocialRepository
from app.schemas import (
    EstadoSocialResponse,
    InicioSocialResponse,
    JugadorResponse,
    RevisarSocialRequest,
)
from app.services.social_service import (
    InicioInvalido,
    ProveedorDesconocido,
    ProveedorNoConfigurado,
    SocialService,
)

router = APIRouter(prefix="/api/auth/social", tags=["Cuentas"])

NOMBRES = {"google": "Google", "github": "GitHub"}


def get_social_service(db: Session = Depends(get_db)) -> SocialService:
    return SocialService(JugadorRepository(db), SocialRepository(db))


@router.post("/revisar", response_model=EstadoSocialResponse)
def revisar_inicio(datos: RevisarSocialRequest, servicio: SocialService = Depends(get_social_service)):
    """US-002 paso 4: el juego pregunta cada 2 segundos si el jugador ya terminó."""
    try:
        estado, jugador, extra = servicio.revisar(datos.codigo_espera)
    except InicioInvalido as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error))

    if estado == "listo":
        return EstadoSocialResponse(
            estado="listo", access_token=extra, jugador=JugadorResponse.model_validate(jugador)
        )
    return EstadoSocialResponse(estado=estado, mensaje=extra)


@router.post("/{proveedor}/iniciar", response_model=InicioSocialResponse)
def iniciar_con_red_social(proveedor: str, servicio: SocialService = Depends(get_social_service)):
    """US-002 paso 1: devuelve la página de Google/GitHub que el juego abre en el navegador."""
    try:
        url, codigo_espera = servicio.iniciar(proveedor)
    except ProveedorDesconocido:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese proveedor no existe")
    except ProveedorNoConfigurado:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"El inicio con {NOMBRES.get(proveedor, proveedor)} todavía no está configurado",
        )
    return InicioSocialResponse(url=url, codigo_espera=codigo_espera)


@router.get("/{proveedor}/callback", response_class=HTMLResponse)
def volver_de_red_social(
    proveedor: str,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    servicio: SocialService = Depends(get_social_service),
):
    """US-002 paso 3: Google/GitHub mandan aquí al jugador. Se le muestra una página
    que le dice que vuelva al juego."""
    try:
        jugador = servicio.completar(proveedor, state, code, error)
    except (InicioInvalido, ProveedorDesconocido, ProveedorNoConfigurado) as problema:
        mensaje = str(problema) or "No se pudo iniciar sesión"
        return HTMLResponse(_pagina("No se pudo iniciar sesión", mensaje, exito=False), status_code=400)
    return HTMLResponse(
        _pagina(
            f"¡Hola, {jugador.nombre_usuario}!",
            "Ya iniciaste sesión. Podés cerrar esta pestaña y volver al juego.",
            exito=True,
        )
    )


def _pagina(titulo: str, mensaje: str, exito: bool) -> str:
    """Página sencilla con los colores del juego."""
    color = "#5adc78" if exito else "#ff5a5a"
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Control del Reactor</title>
<style>
  body {{ background:#141923; color:#fff; font-family:Arial,sans-serif;
         display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
  .panel {{ background:#282d3c; border:2px solid #ffd700; border-radius:10px;
           padding:40px 60px; text-align:center; max-width:420px; }}
  .juego {{ color:#00dcc8; font-size:14px; letter-spacing:2px; }}
  h1 {{ color:{color}; }}
</style></head>
<body><div class="panel">
  <div class="juego">CONTROL DEL REACTOR</div>
  <h1>{escape(titulo)}</h1>
  <p>{escape(mensaje)}</p>
</div></body></html>"""
