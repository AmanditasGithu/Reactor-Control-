import asyncio

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

class ConexionPartida:

    def __init__(self):
        self.conexiones = {}
        self.bloqueo = asyncio.Lock()

    async def conectar(self, id_partida, id_jugador, websocket):

        async with self.bloqueo:

            if id_partida not in self.conexiones:
                self.conexiones[id_partida] = {}

            jugadores = self.conexiones[id_partida]

            if id_jugador in jugadores:
                return False

            await websocket.accept()

            jugadores[id_jugador] = {
                "websocket": websocket,
                "bloqueo_envio": asyncio.Lock()
            }

            return True

    async def desconectar(self, id_partida, id_jugador, websocket):

        async with self.bloqueo:
            jugadores = self.conexiones.get(id_partida)

            if jugadores is None:
                return

            conexion = jugadores.get(id_jugador)

            if conexion is None:
                return

            if conexion["websocket"] is websocket:
                del jugadores[id_jugador]

                if not jugadores:
                    del self.conexiones[id_partida]

    async def enviar_a_jugador(self, id_partida, id_jugador, mensaje):

        async with self.bloqueo:
            jugadores = self.conexiones.get(id_partida, {})
            conexion = jugadores.get(id_jugador)

        if conexion is None:
            return

        websocket = conexion["websocket"]

        try:
            async with conexion["bloqueo_envio"]:
                await websocket.send_json(mensaje)

        except (WebSocketDisconnect, RuntimeError, OSError):
            await self.desconectar(
                id_partida,
                id_jugador,
                websocket
            )

    async def enviar_a_partida(self, id_partida, mensaje):
        async with self.bloqueo:
            jugadores = list(
                self.conexiones.get(id_partida, {}).keys()
            )

        for id_jugador in jugadores:
            await self.enviar_a_jugador(
                id_partida,
                id_jugador,
                mensaje
            )
        