"""Pruebas del perfil (US-006), el ranking (US-022) y el registro de resultados."""
from app.models import Partida
from app.repositories.estadisticas_repository import EstadisticasRepository
from app.services.estadisticas_service import EstadisticasService, ResultadoJugador


def crear_jugador(client, nombre):
    datos = {"nombre_usuario": nombre, "correo": f"{nombre}@correo.com", "contrasena": "clave-segura-1"}
    jugador_id = client.post("/api/auth/registro", json=datos).json()["id"]
    token = client.post(
        "/api/auth/login", json={"usuario_o_correo": nombre, "contrasena": "clave-segura-1"}
    ).json()["access_token"]
    return jugador_id, {"Authorization": f"Bearer {token}"}


def jugar_partida(db, resultados):
    """Simula el final de una partida: [(jugador_id, puntos, posicion), ...]."""
    partida = Partida(escenario="laboratorio", estado="finalizada")
    db.add(partida)
    db.commit()
    servicio = EstadisticasService(EstadisticasRepository(db))
    servicio.registrar_resultado(partida, [ResultadoJugador(*r) for r in resultados])
    return partida


def test_perfil_de_jugador_nuevo(client):
    _, headers = crear_jugador(client, "ana")
    respuesta = client.get("/api/perfil", headers=headers)

    assert respuesta.status_code == 200
    perfil = respuesta.json()
    assert perfil["nombre_usuario"] == "ana"
    assert perfil["correo"] == "ana@correo.com"
    assert perfil["puntos_totales"] == 0
    assert perfil["victorias"] == 0
    assert perfil["historial"] == []
    assert perfil["records"] == []


def test_perfil_sin_sesion_da_error(client):
    assert client.get("/api/perfil").status_code == 401


def test_resultado_actualiza_perfil(client, db):
    ana, headers = crear_jugador(client, "ana")
    luis, _ = crear_jugador(client, "luis")
    jugar_partida(db, [(ana, 450, 1), (luis, 300, 2)])
    jugar_partida(db, [(ana, 200, 2), (luis, 500, 1)])

    perfil = client.get("/api/perfil", headers=headers).json()
    assert perfil["puntos_totales"] == 650
    assert perfil["victorias"] == 1
    assert perfil["partidas_jugadas"] == 2
    assert [p["puntos"] for p in perfil["historial"]] == [200, 450]  # la más reciente primero
    assert perfil["records"][0]["tipo"] == "mayor_puntuacion"
    assert perfil["records"][0]["valor"] == 450


def test_ganador_queda_guardado_en_la_partida(client, db):
    ana, _ = crear_jugador(client, "ana")
    partida = jugar_partida(db, [(ana, 450, 1)])
    assert partida.ganador_id == ana


def test_ranking_ordena_por_puntos(client, db):
    ana, _ = crear_jugador(client, "ana")
    luis, _ = crear_jugador(client, "luis")
    sofi, _ = crear_jugador(client, "sofi")
    jugar_partida(db, [(ana, 300, 2), (luis, 900, 1), (sofi, 100, 3)])

    ranking = client.get("/api/ranking").json()
    assert [f["nombre_usuario"] for f in ranking] == ["luis", "ana", "sofi"]
    assert [f["posicion"] for f in ranking] == [1, 2, 3]


def test_ranking_muestra_maximo_10(client):
    for i in range(12):
        crear_jugador(client, f"jugador{i:02d}")
    assert len(client.get("/api/ranking").json()) == 10


def test_ranking_empatados_comparten_posicion(client):
    crear_jugador(client, "ana")
    crear_jugador(client, "luis")
    ranking = client.get("/api/ranking").json()
    assert [f["posicion"] for f in ranking] == [1, 1]


def test_posicion_en_perfil_coincide_con_ranking(client, db):
    ana, headers = crear_jugador(client, "ana")
    luis, _ = crear_jugador(client, "luis")
    jugar_partida(db, [(ana, 100, 2), (luis, 800, 1)])

    assert client.get("/api/perfil", headers=headers).json()["posicion_ranking"] == 2
