"""Pruebas del menú, el perfil y el ranking, con un backend falso."""
import pygame

from cliente_api import ErrorAPI
from pantallas_menu import PantallaMenu, PantallaPerfil, PantallaRanking

JUGADOR = {"id": 1, "nombre_usuario": "ana_07"}
PERFIL = {
    "nombre_usuario": "ana_07",
    "correo": "ana@correo.com",
    "fecha_registro": "2026-10-25T10:00:00",
    "puntos_totales": 650,
    "victorias": 1,
    "partidas_jugadas": 2,
    "posicion_ranking": 2,
    "historial": [{"partida_id": 2, "escenario": "laboratorio", "fecha": None, "puntos": 200, "posicion": 2}],
    "records": [{"tipo": "mayor_puntuacion", "valor": 450, "fecha": "2026-10-25T10:00:00"}],
}
RANKING = [
    {"posicion": 1, "nombre_usuario": "luis", "puntos_totales": 900, "victorias": 1, "partidas_jugadas": 2},
    {"posicion": 2, "nombre_usuario": "ana_07", "puntos_totales": 650, "victorias": 1, "partidas_jugadas": 2},
]


class ClienteFalso:
    def __init__(self, error=None):
        self.error = error

    def obtener_perfil(self):
        if self.error:
            raise ErrorAPI(self.error)
        return PERFIL

    def obtener_ranking(self, limite=10):
        if self.error:
            raise ErrorAPI(self.error)
        return RANKING


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boton.rect.center)


def test_botones_del_menu(ventana):
    menu = PantallaMenu(ventana, JUGADOR)
    assert menu.manejar_evento(clic(menu.boton_jugar)) == "jugar"
    assert menu.manejar_evento(clic(menu.boton_perfil)) == "ir_a_perfil"
    assert menu.manejar_evento(clic(menu.boton_ranking)) == "ir_a_ranking"
    assert menu.manejar_evento(clic(menu.boton_salir)) == "cerrar_sesion"


def test_perfil_carga_los_datos(ventana):
    perfil = PantallaPerfil(ventana, ClienteFalso())
    assert perfil.datos["puntos_totales"] == 650
    assert perfil.error == ""
    perfil.dibujar()


def test_ranking_carga_los_datos(ventana):
    ranking = PantallaRanking(ventana, ClienteFalso())
    assert [f["nombre_usuario"] for f in ranking.datos] == ["luis", "ana_07"]
    ranking.dibujar()


def test_error_del_servidor_se_muestra(ventana):
    ranking = PantallaRanking(ventana, ClienteFalso(error="No se pudo conectar con el servidor. ¿Está encendido?"))
    assert ranking.datos is None
    assert "servidor" in ranking.error
    ranking.dibujar()


def test_boton_volver(ventana):
    perfil = PantallaPerfil(ventana, ClienteFalso())
    assert perfil.manejar_evento(clic(perfil.boton_volver)) == "volver"


def test_menu_se_dibuja(ventana):
    PantallaMenu(ventana, JUGADOR).dibujar()
