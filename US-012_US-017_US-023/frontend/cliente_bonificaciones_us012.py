"""Cliente de terminal para probar US-012: envía movimientos por WebSocket.

No reemplaza el mando físico y no permite asignarse puntos/bonos.
Ejemplo: python frontend/cliente_bonificaciones_us012.py --partida 1 --jugador 101
"""
import argparse
import json
import threading

from websockets.sync.client import connect


def leer_mensajes(ws, detener):
    try:
        for texto in ws:
            if detener.is_set():
                break
            mensaje = json.loads(texto)
            tipo = mensaje.get('tipo')
            if tipo == 'marcador_actualizado':
                jugadores = mensaje.get('jugadores', [])
                posiciones = ', '.join(f"{j['nombre']}={j['puntos']} pts" for j in jugadores)
                bonus = mensaje.get('bonificacion_disponible')
                disponible = (f" · BONO ({bonus['x']},{bonus['y']})"
                              if bonus else '')
                print(f"\nMarcador: {posiciones}{disponible}")
            elif tipo == 'bonificacion_recogida':
                print(f"\nBono recogido por jugador {mensaje['id_jugador']} "
                      f"(x{mensaje['multiplicador']}, {mensaje['duracion_segundos']} s)")
            elif tipo == 'error':
                print('\nError:', mensaje.get('mensaje'))
    except (Exception,) as exc:
        if not detener.is_set():
            print('\nConexión cerrada:', exc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1:8002')
    parser.add_argument('--partida', type=int, required=True)
    parser.add_argument('--jugador', type=int, required=True)
    args = parser.parse_args()
    url = f"ws://{args.host}/ws/partidas/{args.partida}/{args.jugador}"
    detener = threading.Event()
    with connect(url) as ws:
        hilo = threading.Thread(target=leer_mensajes, args=(ws, detener), daemon=True)
        hilo.start()
        print('W/A/S/D mover arriba/izquierda/abajo/derecha; Q salir')
        try:
            while True:
                letra = input('Movimiento: ').strip().lower()
                if letra == 'q':
                    break
                direccion = {'w': 'ARRIBA', 'a': 'IZQUIERDA',
                             's': 'ABAJO', 'd': 'DERECHA'}.get(letra)
                if direccion:
                    ws.send(json.dumps({'tipo': 'mover', 'direccion': direccion}))
        finally:
            detener.set()


if __name__ == '__main__':
    main()
