"""Pruebas de integración de US-023, con SQLite y TestClient (sin PostgreSQL)."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models import Jugador, Partida, Participacion, ResultadoRecibido, Record
from app.services.historial_service import guardar_finalizacion
from app.schemas import FinalizacionEntrante

SECRET = 'token-interno-test-no-publicar'


def registrar(client, nombre):
    r = client.post('/api/auth/registro', json={
        'nombre_usuario': nombre, 'correo': f'{nombre}@correo.com',
        'contrasena': 'clave-segura-1'})
    assert r.status_code in (200, 201), r.text
    jugador_id = r.json()['id']
    r = client.post('/api/auth/login', json={'usuario_o_correo': nombre, 'contrasena': 'clave-segura-1'})
    assert r.status_code == 200, r.text
    return jugador_id, {'Authorization': f"Bearer {r.json()['access_token']}"}


def resultado(ana, luis, puntos=(45, 20), id_externo=None):
    fin = datetime.now(timezone.utc)
    return {
        'id_externo': id_externo or uuid4().hex,
        'escenario': 'laboratorio',
        'inicio_utc': (fin - timedelta(seconds=60)).isoformat(),
        'fin_utc': fin.isoformat(),
        'duracion_segundos': 180,
        'puntuacion_objetivo': 100,
        'motivo_fin': 'TIEMPO',
        'resultados_finales': [
            {'id_jugador': ana, 'puntos': puntos[0]},
            {'id_jugador': luis, 'puntos': puntos[1]},
        ],
    }


def enviar(client, datos, clave=SECRET):
    return client.post('/api/interno/resultados', json=datos,
                       headers={'X-Reactor-Servicio': clave})


def test_guardado_consulta_historial_y_records(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, h_ana = registrar(client, 'ana')
    luis, h_luis = registrar(client, 'luis')
    r = enviar(client, resultado(ana, luis))
    assert r.status_code == 200, r.text
    assert r.json()['duplicado'] is False
    id_bd = r.json()['partida_id']

    historial = client.get('/api/historial', headers=h_ana).json()
    assert historial['total'] == 1
    assert historial['partidas'][0]['partida_id'] == id_bd
    assert historial['partidas'][0]['puntos'] == 45
    assert historial['partidas'][0]['motivo_fin'] == 'TIEMPO'

    detalle = client.get(f'/api/historial/{id_bd}', headers=h_luis)
    assert detalle.status_code == 200
    assert len(detalle.json()['participantes']) == 2
    assert detalle.json()['ganador_id'] == ana
    assert detalle.json()['participantes'][0]['nombre_usuario'] == 'ana'

    records = client.get('/api/records', headers=h_ana).json()
    assert len(records) == 1
    assert records[0]['tipo'] == 'mayor_puntuacion'
    assert records[0]['valor'] == 45
    assert db.get(Jugador, ana).puntos_totales == 45
    assert db.get(Jugador, ana).victorias == 1
    assert db.get(Jugador, luis).partidas_jugadas == 1


def test_duplicado_no_suma_dos_veces(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, _ = registrar(client, 'ana')
    luis, _ = registrar(client, 'luis')
    datos = resultado(ana, luis)
    assert enviar(client, datos).json()['duplicado'] is False
    reenvio = enviar(client, datos)
    assert reenvio.status_code == 200
    assert reenvio.json()['duplicado'] is True
    assert db.get(Jugador, ana).puntos_totales == 45
    assert db.get(Jugador, ana).partidas_jugadas == 1
    assert db.query(Partida).count() == 1
    assert db.query(ResultadoRecibido).count() == 1


def test_reenvio_alterado_se_rechaza(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, _ = registrar(client, 'ana')
    luis, _ = registrar(client, 'luis')
    datos = resultado(ana, luis)
    assert enviar(client, datos).status_code == 200
    cambiado = {**datos, 'resultados_finales': [
        {'id_jugador': ana, 'puntos': 60}, {'id_jugador': luis, 'puntos': 20}]}
    r = enviar(client, cambiado)
    assert r.status_code == 409
    assert db.get(Jugador, ana).puntos_totales == 45


def test_solo_servidor_puede_enviar_resultados(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    r = client.post('/api/interno/resultados', json={})
    assert r.status_code in (403, 422)
    assert db.query(Partida).count() == 0


def test_clave_incorrecta_rechazada(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, _ = registrar(client, 'ana')
    luis, _ = registrar(client, 'luis')
    assert enviar(client, resultado(ana,luis), 'incorrecta').status_code == 403
    assert db.query(Partida).count() == 0


def test_falta_jugador_hace_rollback_total(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, _ = registrar(client, 'ana')
    r = enviar(client, resultado(ana, 99999))
    assert r.status_code == 422
    assert db.query(Partida).count() == 0
    assert db.query(ResultadoRecibido).count() == 0
    assert db.get(Jugador, ana).puntos_totales == 0


def test_historial_paginado_y_record_maximo(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, headers = registrar(client, 'ana')
    luis, _ = registrar(client, 'luis')
    for p in (20, 30, 45):
        assert enviar(client, resultado(ana, luis, (p, 10))).status_code == 200
    hist = client.get('/api/historial?limite=2&offset=1', headers=headers).json()
    assert hist['total'] == 3
    assert len(hist['partidas']) == 2
    assert client.get('/api/records', headers=headers).json()[0]['valor'] == 45
    assert db.get(Jugador, ana).puntos_totales == 95


def test_el_historial_privado_necesita_sesion(client, monkeypatch):
    assert client.get('/api/historial').status_code == 401
    assert client.get('/api/records').status_code == 401
    assert client.get('/api/historial/1').status_code == 401


def test_otros_jugadores_no_ven_partida_privada(client, monkeypatch):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, _ = registrar(client, 'ana')
    luis, _ = registrar(client, 'luis')
    _, headers = registrar(client, 'sofi')
    r = enviar(client, resultado(ana, luis))
    assert r.status_code == 200
    id_bd = r.json()['partida_id']
    assert client.get(f'/api/historial/{id_bd}', headers=headers).status_code == 404
    assert client.get('/api/historial', headers=headers).json()['total'] == 0


def test_entrada_invalida_rechaza_ids_repetidos(client, monkeypatch, db):
    monkeypatch.setenv('REACTOR_RESULTADOS_TOKEN', SECRET)
    ana, _ = registrar(client, 'ana')
    datos = resultado(ana, ana)
    assert enviar(client, datos).status_code == 422
    assert db.query(Partida).count() == 0


def test_secret_sin_configurar_falla_cerrado(client, monkeypatch):
    monkeypatch.delenv('REACTOR_RESULTADOS_TOKEN', raising=False)
    ana, _ = registrar(client, 'ana')
    luis, _ = registrar(client, 'luis')
    assert enviar(client, resultado(ana, luis)).status_code == 503
