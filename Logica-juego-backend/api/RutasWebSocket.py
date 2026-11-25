import json

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from servicios.EstadoServidor import gestor, conexiones, marcador

router = APIRouter()

SENALES_ACCION = {'ACCION_PRESIONAR', 'ACCION_LATIDO', 'ACCION_SOLTAR'}

@router.websocket('/ws/partidas/{id_partida}/{id_jugador}')
async def conectar_jugador(websocket: WebSocket, id_partida: int, id_jugador: int):
    if not gestor.jugador_en_partida(id_partida, id_jugador):
        await websocket.close(code=1008)
        return
    conectado = await conexiones.conectar(id_partida, id_jugador, websocket)
    if not conectado:
        await websocket.close(code=1008)
        return
    try:
        await conexiones.enviar_a_jugador(id_partida, id_jugador, {
            'tipo': 'estado', 'partida': gestor.obtener_estado(id_partida)
        })
        await conexiones.enviar_a_jugador(
            id_partida, id_jugador, marcador.evento_actual(gestor.obtener_estado(id_partida))
        )
        await conexiones.enviar_a_partida(id_partida, {'tipo': 'jugador_conectado', 'id_jugador': id_jugador})
        while True:
            try:
                datos = await websocket.receive_json()
            except json.JSONDecodeError:
                await conexiones.enviar_a_jugador(id_partida, id_jugador, {'tipo': 'error', 'mensaje': 'JSON inválido'})
                continue
            if not isinstance(datos, dict):
                await conexiones.enviar_a_jugador(id_partida, id_jugador, {'tipo': 'error', 'mensaje': 'Formato inválido'})
                continue
            if datos.get('tipo') == 'mover':
                resultado = gestor.mover_jugador_detallado(
                    id_partida, id_jugador, datos.get('direccion')
                )
                if not resultado['ok']:
                    await conexiones.enviar_a_jugador(
                        id_partida, id_jugador,
                        {'tipo': 'error', 'mensaje': 'Movimiento no permitido'}
                    )
                    continue

                await conexiones.enviar_a_partida(id_partida, {
                    'tipo': 'estado', 'partida': resultado['estado']
                })
                await marcador.publicar_si_cambia(resultado['estado'], conexiones)

                if resultado.get('bonificacion_recogida') is not None:
                    await conexiones.enviar_a_partida(id_partida, {
                        'tipo': 'bonificacion_recogida',
                        **resultado['bonificacion_recogida'],
                    })

                if resultado['terminal_activada'] is not None:
                    await conexiones.enviar_a_partida(id_partida, {
                        'tipo': 'terminal_activada',
                        **resultado['terminal_activada']
                    })
            elif datos.get('tipo') == 'accion':
                # US-024: el botón EXTRAER del celular hace lo mismo que el control físico:
                # ACCION_PRESIONAR al tocarlo, ACCION_LATIDO mientras se mantiene y ACCION_SOLTAR al soltarlo.
                senal = datos.get('senal')
                if senal not in SENALES_ACCION:
                    await conexiones.enviar_a_jugador(id_partida, id_jugador, {'tipo': 'error', 'mensaje': 'Señal no válida'})
                    continue
                resultado = gestor.procesar_senal_accion(id_partida, id_jugador, senal)
                if not resultado['ok'] and senal == 'ACCION_PRESIONAR':
                    await conexiones.enviar_a_jugador(id_partida, id_jugador, {'tipo': 'aviso', 'mensaje': resultado['mensaje']})
                if resultado['cambio']:
                    estado = gestor.obtener_estado(id_partida)
                    await conexiones.enviar_a_partida(id_partida, {'tipo': 'estado', 'partida': estado})
                    await marcador.publicar_si_cambia(estado, conexiones)
            else:
                await conexiones.enviar_a_jugador(id_partida, id_jugador, {'tipo': 'error', 'mensaje': 'Acción desconocida'})
    except WebSocketDisconnect:
        pass
    finally:
        await conexiones.desconectar(id_partida, id_jugador, websocket)
        await conexiones.enviar_a_partida(id_partida, {'tipo': 'jugador_desconectado', 'id_jugador': id_jugador})