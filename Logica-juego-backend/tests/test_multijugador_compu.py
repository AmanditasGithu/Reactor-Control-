"""Multijugador de la arena de la compu: mapa, posiciones y celdas compartidas."""
from fastapi.testclient import TestClient


def _partida(cliente, escenario="complejo_militar"):
    id_partida = cliente.post('/partidas', json={'escenario': escenario}).json()['id_partida']
    for id_jugador, nombre in ((701, 'Ana'), (702, 'Beto')):
        cliente.post(f'/partidas/{id_partida}/unirse', json={'id_jugador': id_jugador, 'nombre': nombre})
    cliente.post(f'/partidas/{id_partida}/iniciar')
    return id_partida


def _esperar(ws, condicion, intentos=25):
    for _ in range(intentos):
        evento = ws.receive_json()
        if evento.get('tipo') == 'estado' and condicion(evento['partida']):
            return evento['partida']
    raise AssertionError('No llegó el estado esperado')


def test_la_partida_guarda_el_escenario():
    from main import app
    with TestClient(app) as cliente:
        id_partida = _partida(cliente)
        assert cliente.get(f'/partidas/{id_partida}').json()['escenario'] == 'complejo_militar'


def test_la_arena_configura_el_mapa_y_se_mueve_por_casillas():
    from main import app
    with TestClient(app) as cliente:
        id_partida = _partida(cliente)
        with cliente.websocket_connect(f'/ws/partidas/{id_partida}/701') as ws:
            ws.send_json({'tipo': 'configurar', 'reactor': [19, 5], 'terminales': [[2, 2], [30, 11]],
                          'celdas': [[7, 1]], 'bonificaciones': [[5, 5]]})
            estado = _esperar(ws, lambda p: p['reactor']['x'] == 19)
            assert [(t['x'], t['y']) for t in estado['terminales']] == [(2, 2), (30, 11)]
            assert estado['celdas'] == [[7, 1]]

            ws.send_json({'tipo': 'posicion', 'x': 1, 'y': 2})   # primera vez: donde empieza
            _esperar(ws, lambda p: (p['jugadores'][0]['x'], p['jugadores'][0]['y']) == (1, 2))
            ws.send_json({'tipo': 'posicion', 'x': 2, 'y': 2})   # llega a la terminal
            estado = _esperar(ws, lambda p: p['jugadores'][0]['x'] == 2)
            assert estado['jugadores'][0]['puntos'] == 10


def test_no_se_puede_teletransportar():
    from main import app
    from servicios.EstadoServidor import gestor
    with TestClient(app) as cliente:
        id_partida = _partida(cliente)
        assert gestor.ubicar_jugador(id_partida, 701, 1, 1)['ok']
        assert not gestor.ubicar_jugador(id_partida, 701, 20, 9)['ok']


def test_la_celda_es_de_quien_la_toca_primero():
    from main import app
    from servicios.EstadoServidor import gestor
    with TestClient(app) as cliente:
        id_partida = _partida(cliente)
        gestor.configurar_mapa(id_partida, (19, 5), [(2, 2)], [], [(7, 1)])
        gestor.ubicar_jugador(id_partida, 701, 6, 1)
        gestor.ubicar_jugador(id_partida, 702, 8, 1)
        assert gestor.recoger_celda(id_partida, 701, 7, 1) is not None
        assert gestor.recoger_celda(id_partida, 702, 7, 1) is None  # ya no está
        partida = gestor.obtener_estado(id_partida)
        assert partida['jugadores'][0]['puntos'] == 10 and partida['celdas'] == []
