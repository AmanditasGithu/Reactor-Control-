import asyncio

from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI

from api.RutasdePartida import router as rutas_partidas
from api.RutasWebSocket import router as rutas_websocket
from api.RutasHardware import router as rutas_hardware
from servicios.EstadoServidor import gestor, conexiones


async def ciclo_reactor():

    while True:
        await asyncio.sleep(0.1)
        cambios = gestor.procesar_extracciones()
        finales = gestor.consumir_finalizaciones()

        for id_partida, estado in cambios:
            await conexiones.enviar_a_partida(id_partida, {
                'tipo': 'estado', 'partida': estado
            })

        for id_partida, estado in finales:
            await conexiones.enviar_a_partida(id_partida, {
                'tipo': 'partida_finalizada',
                'id_partida': id_partida,
                'motivo_fin': estado['motivo_fin'],
                'resultados_finales': estado['resultados_finales'],
                'partida': estado}
            )

@asynccontextmanager
async def lifespan(app: FastAPI):
    tarea = asyncio.create_task(ciclo_reactor())

    try:
        yield
    finally:
        tarea.cancel()
        with suppress(asyncio.CancelledError):
            await tarea

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