"""El juego de la compu guarda las partidas en el perfil y el ranking."""
from uuid import uuid4

from tests.test_perfil_ranking import crear_jugador


def partida(puntos, motivo="TIEMPO", id_externo=None):
    return {
        "id_externo": id_externo or uuid4().hex,
        "escenario": "planta_industrial",
        "inicio_utc": "2026-11-25T20:00:00+00:00",
        "fin_utc": "2026-11-25T20:03:00+00:00",
        "duracion_segundos": 180,
        "puntuacion_objetivo": 100,
        "motivo_fin": motivo,
        "puntos": puntos,
    }


def test_la_partida_suma_al_perfil_y_al_ranking(client):
    _, cabecera = crear_jugador(client, "ana")
    respuesta = client.post("/api/partidas/local", json=partida(70), headers=cabecera)
    assert respuesta.status_code == 200, respuesta.text
    client.post("/api/partidas/local", json=partida(120, "PUNTUACION"), headers=cabecera)

    perfil = client.get("/api/perfil", headers=cabecera).json()
    assert perfil["puntos_totales"] == 190
    assert perfil["partidas_jugadas"] == 2
    assert perfil["victorias"] == 1  # solo la que llegó a la meta
    ranking = client.get("/api/ranking").json()
    assert ranking[0]["nombre_usuario"] == "ana" and ranking[0]["puntos_totales"] == 190


def test_reenviar_la_misma_partida_no_cuenta_doble(client):
    _, cabecera = crear_jugador(client, "beto")
    datos = partida(50)
    client.post("/api/partidas/local", json=datos, headers=cabecera)
    otra_vez = client.post("/api/partidas/local", json=datos, headers=cabecera)
    assert otra_vez.json()["duplicado"] is True
    assert client.get("/api/perfil", headers=cabecera).json()["puntos_totales"] == 50


def test_sin_sesion_no_se_guarda(client):
    assert client.post("/api/partidas/local", json=partida(50)).status_code == 401
