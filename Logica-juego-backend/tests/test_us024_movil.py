"""US-024: jugar desde el celular contra el servidor de partidas."""

from fastapi.testclient import TestClient


def _partida_iniciada(cliente):
    id_partida = cliente.post('/partidas').json()['id_partida']
    for id_jugador, nombre in ((501, 'Ana'), (502, 'Beto')):
        assert cliente.post(f'/partidas/{id_partida}/unirse', json={
            'id_jugador': id_jugador, 'nombre': nombre}).status_code == 200
    assert cliente.post(f'/partidas/{id_partida}/iniciar').status_code == 200
    return id_partida


def _esperar(ws, tipo, condicion=lambda e: True, intentos=20):
    for _ in range(intentos):
        evento = ws.receive_json()
        if evento.get('tipo') == tipo and condicion(evento):
            return evento
    raise AssertionError(f'No llegó {tipo}')


def test_la_pagina_del_celular_puede_llamar_al_servidor():
    """El celular abre la página en el puerto 8000 y llama a este servidor (8002)."""
    from main import app
    with TestClient(app) as cliente:
        respuesta = cliente.options('/partidas', headers={
            'Origin': 'http://192.168.0.10:8000',
            'Access-Control-Request-Method': 'POST',
        })
        assert respuesta.status_code == 200
        assert respuesta.headers['access-control-allow-origin'] in ('*', 'http://192.168.0.10:8000')


def test_extraer_desde_el_celular_suma_puntos():
    from main import app
    from servicios.EstadoServidor import gestor
    with TestClient(app) as cliente:
        id_partida = _partida_iniciada(cliente)
        with gestor.bloqueo:
            ana = gestor._jugador(gestor.partidas[id_partida], 501)
            ana.x, ana.y = 4, 4  # dentro del radio del reactor (5, 5)
        with cliente.websocket_connect(f'/ws/partidas/{id_partida}/501') as ws:
            ws.send_json({'tipo': 'accion', 'senal': 'ACCION_PRESIONAR'})
            evento = _esperar(ws, 'estado', lambda e: e['partida']['jugadores'][0]['extrayendo'])
            assert evento['partida']['jugadores'][0]['puntos'] > 0
            ws.send_json({'tipo': 'accion', 'senal': 'ACCION_SOLTAR'})
            _esperar(ws, 'estado', lambda e: not e['partida']['jugadores'][0]['extrayendo'])


def test_extraer_lejos_del_reactor_avisa():
    from main import app
    with TestClient(app) as cliente:
        id_partida = _partida_iniciada(cliente)
        with cliente.websocket_connect(f'/ws/partidas/{id_partida}/501') as ws:
            ws.send_json({'tipo': 'accion', 'senal': 'ACCION_PRESIONAR'})
            aviso = _esperar(ws, 'aviso')
            assert aviso['mensaje'] == 'Fuera de rango'


def test_senal_inventada_se_rechaza():
    from main import app
    with TestClient(app) as cliente:
        id_partida = _partida_iniciada(cliente)
        with cliente.websocket_connect(f'/ws/partidas/{id_partida}/501') as ws:
            ws.send_json({'tipo': 'accion', 'senal': 'SUMAR_100_PUNTOS'})
            error = _esperar(ws, 'error')
            assert error['mensaje'] == 'Señal no válida'
