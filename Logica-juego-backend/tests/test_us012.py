"""US-012: generación, recolección, expiración y comunicación de bonificaciones."""
import time

from fastapi.testclient import TestClient

from modelos.Bonificacion import Bonificacion
from modelos.Jugador import Jugador
from modelos.Partida import Partida
from servicios.GestorBonificaciones import GestorBonificaciones
from servicios.GestordePartida import GestordePartida
from servicios.MarcadorTiempoReal import MarcadorTiempoReal


def construir_partida():
    partida = Partida(999, duracion=180, meta=200)
    uno, dos = Jugador(1, 'Carlos'), Jugador(2, 'Ana')
    partida.agregar_jugador(uno)
    partida.agregar_jugador(dos)
    assert partida.iniciar_partida()
    return partida, uno, dos


def test_bono_se_genera_en_tiempo_programado_y_es_visible():
    p, a, b = construir_partida()
    gestor = GestorBonificaciones()
    inicio = p.inicio_monotonico
    assert not gestor.actualizar(p, inicio + 7.9)
    assert p.bonificacion_disponible is None
    assert gestor.actualizar(p, inicio + 8.0)
    objeto = p.bonificacion_disponible
    assert objeto.tipo == 'DOBLE_PUNTOS'
    assert (objeto.x, objeto.y) in gestor.POSICIONES
    assert objeto.obtener_estado(inicio + 8)['segundos_restantes'] == 12
    assert not gestor.actualizar(p, inicio + 8.1)
    assert p.bonificacion_disponible.id_bonificacion == objeto.id_bonificacion


def test_primer_jugador_recoge_y_segundo_no_puede_duplicar():
    p, uno, dos = construir_partida()
    gestor = GestorBonificaciones()
    ahora = p.inicio_monotonico + 8
    assert gestor.actualizar(p, ahora)
    bono = p.bonificacion_disponible
    uno.x, uno.y = bono.x, bono.y
    dos.x, dos.y = bono.x, bono.y
    recogida = gestor.intentar_recoger(p, uno, ahora + 0.1)
    assert recogida['id_jugador'] == 1
    assert recogida['multiplicador'] == 2
    assert gestor.intentar_recoger(p, dos, ahora + 0.1) is None
    assert p.bonificacion_disponible is None
    assert uno.bonificacion_activa is not None
    assert dos.bonificacion_activa is None


def test_efecto_x2_y_caducidad_sin_puntos_extra_automaticos():
    p, uno, _ = construir_partida()
    gestor = GestorBonificaciones()
    ahora = p.inicio_monotonico + 8
    gestor.actualizar(p, ahora)
    bono = p.bonificacion_disponible
    uno.x, uno.y = bono.x, bono.y
    gestor.intentar_recoger(p, uno, ahora)
    assert uno.puntos == 0
    assert uno.sumar_puntos(5, ahora=ahora + 4) == 10
    assert uno.puntos == 10
    assert uno.sumar_puntos(5, ahora=ahora + 8) == 5
    assert uno.sumar_puntos(-3, ahora=ahora + 4) == -3
    assert uno.puntos == 12
    assert gestor.actualizar(p, ahora + 8)
    assert uno.bonificacion_activa is None


def test_extraer_reactor_con_bono_duplica_puntos_no_energia():
    p, uno, _ = construir_partida()
    gestor = GestorBonificaciones()
    ahora = p.inicio_monotonico + 8
    gestor.actualizar(p, ahora)
    bono = p.bonificacion_disponible
    uno.x, uno.y = bono.x, bono.y
    gestor.intentar_recoger(p, uno, ahora)
    uno.x, uno.y = 5, 4
    energia_antes = p.reactor.energia_actual
    cantidad = p.reactor.extraer(uno, ahora + 1)
    assert cantidad == 5
    assert energia_antes - p.reactor.energia_actual == 5
    assert uno.puntos == 10


def test_bono_aplica_a_terminal_solo_una_vez():
    p, uno, _ = construir_partida()
    gestor = GestorBonificaciones()
    ahora = p.inicio_monotonico + 8
    gestor.actualizar(p, ahora)
    bono = p.bonificacion_disponible
    uno.x, uno.y = bono.x, bono.y
    gestor.intentar_recoger(p, uno, ahora)
    terminal = p.terminales[0]
    uno.x, uno.y = terminal.x, terminal.y
    assert terminal.activar(uno, ahora=ahora + 1)
    assert uno.puntos == 20
    assert not terminal.activar(uno, ahora=ahora + 2)
    assert uno.puntos == 20


def test_bonificacion_no_recogida_caduca_y_reaparece():
    p, _, _ = construir_partida()
    gestor = GestorBonificaciones()
    t = p.inicio_monotonico + 8
    gestor.actualizar(p, t)
    primer_id = p.bonificacion_disponible.id_bonificacion
    assert gestor.actualizar(p, t + 12)
    assert p.bonificacion_disponible is None
    assert gestor.actualizar(p, t + 15)
    assert p.bonificacion_disponible.id_bonificacion == primer_id + 1


def test_no_generar_sobre_jugador_presente():
    p, uno, dos = construir_partida()
    uno.x, uno.y = (4, 4)
    dos.x, dos.y = (6, 4)
    gestor = GestorBonificaciones()
    assert gestor.actualizar(p, p.inicio_monotonico + 8)
    b = p.bonificacion_disponible
    assert (b.x, b.y) not in ((4, 4), (6, 4))


def test_no_generar_despues_de_finalizar():
    p, uno, _ = construir_partida()
    g = GestorBonificaciones()
    p.estado = 'FINALIZADA'
    assert not g.actualizar(p, p.inicio_monotonico + 9)
    assert p.bonificacion_disponible is None


def test_servidor_detecta_recogida_y_notifica_estado():
    gestor = GestordePartida()
    p = gestor.crear_partida()
    uno, dos = Jugador(1, 'Carlos'), Jugador(2, 'Ana')
    assert gestor.unir_jugador(p.id_partida, uno)
    assert gestor.unir_jugador(p.id_partida, dos)
    assert gestor.iniciar_partida(p.id_partida)
    ahora = time.monotonic()
    with gestor.bloqueo:
        uno.x, uno.y = 3, 4
        p.bonificacion_disponible = Bonificacion(
            id_bonificacion=1, x=4, y=4,
            caduca_en=ahora + 30, duracion_efecto=8
        )
    resultado = gestor.mover_jugador_detallado(p.id_partida, 1, 'DERECHA')
    assert resultado['ok']
    assert resultado['bonificacion_recogida']['id_jugador'] == 1
    assert resultado['estado']['jugadores'][0]['bonificacion']['multiplicador'] == 2
    assert resultado['estado']['bonificacion_disponible'] is None


def test_marcador_publica_nuevo_bono_y_efecto_sin_puntos_nuevos():
    gestor = GestordePartida()
    p = gestor.crear_partida()
    gestor.unir_jugador(p.id_partida, Jugador(1, 'Carlos'))
    gestor.unir_jugador(p.id_partida, Jugador(2, 'Ana'))
    gestor.iniciar_partida(p.id_partida)
    marcador = MarcadorTiempoReal()
    inicial = marcador.evento_actual(gestor.obtener_estado(p.id_partida))
    with gestor.bloqueo:
        p.bonificacion_disponible = Bonificacion(1, 4, 4, time.monotonic() + 8, 8)
    cambio = marcador.evento_si_cambia(gestor.obtener_estado(p.id_partida))
    assert cambio is not None
    assert cambio['revision'] == inicial['revision'] + 1
    assert cambio['bonificacion_disponible']['x'] == 4
    assert marcador.evento_si_cambia(gestor.obtener_estado(p.id_partida)) is None


def test_finalizacion_quita_efectos_sin_perder_puntos():
    gestor = GestordePartida()
    p = gestor.crear_partida()
    uno, dos = Jugador(1, 'Carlos'), Jugador(2, 'Ana')
    gestor.unir_jugador(p.id_partida, uno)
    gestor.unir_jugador(p.id_partida, dos)
    gestor.iniciar_partida(p.id_partida)
    with gestor.bloqueo:
        t = time.monotonic()
        p.bonificacion_disponible = Bonificacion(1, 4, 4, t + 8, 8)
        uno.x, uno.y = 4, 4
        gestor.bonificaciones.intentar_recoger(p, uno, t)
        uno.puntos = p.meta - 5
        assert uno.sumar_puntos(5, ahora=t + 1) == 10
        assert gestor._verificar_fin(p, t + 1)
    estado = gestor.obtener_estado(p.id_partida)
    assert estado['estado'] == 'FINALIZADA'
    assert uno.puntos == p.meta + 5
    assert estado['jugadores'][0]['bonificacion'] is None
    assert estado['bonificacion_disponible'] is None


def test_dos_websockets_reciben_recogida_y_marcador(monkeypatch):
    from main import app
    from servicios.EstadoServidor import gestor

    with TestClient(app) as client:
        id_partida = client.post('/partidas').json()['id_partida']
        assert client.post(f'/partidas/{id_partida}/unirse', json={
            'id_jugador': 311, 'nombre': 'Carlos'}).status_code == 200
        assert client.post(f'/partidas/{id_partida}/unirse', json={
            'id_jugador': 312, 'nombre': 'Ana'}).status_code == 200
        assert client.post(f'/partidas/{id_partida}/iniciar').status_code == 200
        with gestor.bloqueo:
            p = gestor.partidas[id_partida]
            uno = gestor._jugador(p, 311)
            uno.x, uno.y = 3, 4
            p.bonificacion_disponible = Bonificacion(
                900, 4, 4, time.monotonic() + 30, 8
            )
        with client.websocket_connect(f'/ws/partidas/{id_partida}/311') as ws1:
            with client.websocket_connect(f'/ws/partidas/{id_partida}/312') as ws2:
                ws1.send_json({'tipo': 'mover', 'direccion': 'DERECHA'})
                def recoger_eventos(ws):
                    vistos = set()
                    for _ in range(12):
                        e = ws.receive_json()
                        if e.get('tipo') == 'bonificacion_recogida':
                            assert e['id_jugador'] == 311
                            vistos.add('recogida')
                        if e.get('tipo') == 'marcador_actualizado' and any(
                            j.get('bonificacion') for j in e.get('jugadores', [])
                        ):
                            vistos.add('marcador')
                        if vistos == {'recogida', 'marcador'}:
                            return
                    assert False, f'Faltaron eventos {vistos}'
                recoger_eventos(ws1)
                recoger_eventos(ws2)


def test_endpoint_estado_expone_bono_sin_permitir_fijar_puntos():
    from main import app
    from servicios.EstadoServidor import gestor
    with TestClient(app) as cliente:
        id_partida = cliente.post('/partidas').json()['id_partida']
        assert cliente.get(f'/partidas/{id_partida}/estado').status_code == 200
        respuesta = cliente.get(f'/partidas/{id_partida}/estado').json()
        assert respuesta['bonificacion_disponible'] is None
        assert respuesta['jugadores'] == []
        assert cliente.get('/partidas/999999/estado').status_code == 404
