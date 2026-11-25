import asyncio

from contextlib import asynccontextmanager, suppress
import logging
from fastapi import FastAPI

from api.RutasdePartida import router as rutas_partidas
from api.RutasWebSocket import router as rutas_websocket
from api.RutasHardware import router as rutas_hardware
from servicios.EstadoServidor import gestor, conexiones, marcador
from servicios.EnvioResultados import EnvioResultados

LOG = logging.getLogger(__name__)


async def ciclo_reactor(envio_resultados):

    while True:
        await asyncio.sleep(0.1)
        cambios = gestor.procesar_extracciones()
        finales = gestor.consumir_finalizaciones()

        for id_partida, estado in cambios:
            await conexiones.enviar_a_partida(id_partida, {
                'tipo': 'estado', 'partida': estado
            })
            await marcador.publicar_si_cambia(estado, conexiones)

        for id_partida, estado in finales:
            # Se conserva el resultado antes de enviarlo a PostgreSQL.
            # La comunicación externa se efectúa desde otro worker.
            try:
                envio_resultados.agregar(estado)
            except Exception:
                LOG.exception("Error al poner el resultado en la bandeja local")
            await conexiones.enviar_a_partida(id_partida, {
                'tipo': 'partida_finalizada',
                'id_partida': id_partida,
                'motivo_fin': estado['motivo_fin'],
                'resultados_finales': estado['resultados_finales'],
                'partida': estado}
            )
            await marcador.publicar_si_cambia(estado, conexiones)

async def ciclo_envio_resultados(envio_resultados):
    while True:
        # Una API temporalmente caída no detiene la partida ni destruye la cola.
        try:
            await asyncio.to_thread(envio_resultados.enviar_pendientes)
        except Exception:
            LOG.exception("Error inesperado en el envío de resultados")
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    envio_resultados = EnvioResultados()
    tarea = asyncio.create_task(ciclo_reactor(envio_resultados))
    tarea_envios = asyncio.create_task(ciclo_envio_resultados(envio_resultados))
    try:
        yield
    finally:
        tarea.cancel()
        tarea_envios.cancel()
        for pendiente in (tarea, tarea_envios):
            with suppress(asyncio.CancelledError):
                await pendiente

app = FastAPI(
    title = "Control del Reactor",
    description = "API del juego multijugador",
    version = "1.0.0",
    lifespan = lifespan
)

app.include_router(rutas_partidas)
app.include_router(rutas_websocket)
app.include_router(rutas_hardware)

@app.get("/")

def inicio():
    return {
        "mensaje": "Servidor de Control de Reactor activo"
    }