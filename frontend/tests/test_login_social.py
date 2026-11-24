"""Pruebas del login con Google/GitHub (US-002), con un backend falso y sin abrir el navegador."""
import pygame
import pytest

from cliente_api import ClienteAPI, ErrorAPI
from pantallas_cuentas import PantallaEsperandoNavegador, PantallaLogin

INICIO = {"url": "https://accounts.google.com/o/oauth2/v2/auth?state=abc", "codigo_espera": "espera-123"}


class ClienteFalso:
    def __init__(self, respuestas=None, error=None):
        self.respuestas = list(respuestas or [])  # lo que responde cada vez que se revisa
        self.error = error
        self.llamadas = []

    def iniciar_login_social(self, proveedor):
        self.llamadas.append(("iniciar", proveedor))
        if self.error:
            raise ErrorAPI(self.error)
        return INICIO

    def revisar_login_social(self, codigo_espera):
        self.llamadas.append(("revisar", codigo_espera))
        if self.error:
            raise ErrorAPI(self.error)
        return self.respuestas.pop(0)


@pytest.fixture
def navegador(monkeypatch):
    """Guarda las páginas que se habrían abierto en el navegador."""
    abiertas = []
    monkeypatch.setattr(PantallaLogin, "abrir_navegador", staticmethod(abiertas.append))
    return abiertas


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boton.rect.center)


def pantalla_esperando(ventana, cliente):
    pantalla = PantallaEsperandoNavegador(ventana, cliente, "google", INICIO)
    pantalla.ultima_pregunta = -10_000  # para que pregunte de una vez
    return pantalla


def test_login_tiene_botones_de_google_y_github(ventana):
    pantalla = PantallaLogin(ventana, ClienteFalso())
    assert "Google" in pantalla.boton_google.texto
    assert "GitHub" in pantalla.boton_github.texto
    pantalla.dibujar()  # no se sale de la ventana ni da error


def test_los_botones_caben_en_la_ventana(ventana):
    pantalla = PantallaLogin(ventana, ClienteFalso())
    for boton in pantalla.botones:
        assert ventana.get_rect().contains(boton.rect)


def test_clic_en_google_abre_el_navegador(ventana, navegador):
    cliente = ClienteFalso()
    pantalla = PantallaLogin(ventana, cliente)
    accion = pantalla.manejar_evento(clic(pantalla.boton_google))

    assert cliente.llamadas == [("iniciar", "google")]
    assert navegador == [INICIO["url"]]
    assert accion == ("esperando_navegador", ("google", INICIO))


def test_clic_en_github(ventana, navegador):
    cliente = ClienteFalso()
    pantalla = PantallaLogin(ventana, cliente)
    pantalla.manejar_evento(clic(pantalla.boton_github))
    assert cliente.llamadas == [("iniciar", "github")]


def test_si_no_esta_configurado_muestra_el_error(ventana, navegador):
    pantalla = PantallaLogin(ventana, ClienteFalso(error="El inicio con Google todavía no está configurado"))
    accion = pantalla.manejar_evento(clic(pantalla.boton_google))

    assert accion is None
    assert navegador == []
    assert "no está configurado" in pantalla.mensaje


def test_espera_mientras_esta_pendiente(ventana):
    cliente = ClienteFalso([{"estado": "pendiente"}])
    pantalla = pantalla_esperando(ventana, cliente)

    assert pantalla.actualizar() is None
    assert cliente.llamadas == [("revisar", "espera-123")]


def test_no_pregunta_en_cada_cuadro(ventana):
    cliente = ClienteFalso([{"estado": "pendiente"}, {"estado": "pendiente"}])
    pantalla = pantalla_esperando(ventana, cliente)
    pantalla.actualizar()
    pantalla.actualizar()  # enseguida: todavía no pasaron 2 segundos
    assert len(cliente.llamadas) == 1


def test_cuando_termina_inicia_sesion(ventana):
    jugador = {"id": 1, "nombre_usuario": "Ana_Perez"}
    pantalla = pantalla_esperando(ventana, ClienteFalso([{"estado": "listo", "jugador": jugador}]))
    assert pantalla.actualizar() == ("sesion_iniciada", jugador)


def test_si_falla_vuelve_con_el_mensaje(ventana):
    cliente = ClienteFalso([{"estado": "error", "mensaje": "Cancelaste el inicio de sesión"}])
    pantalla = pantalla_esperando(ventana, cliente)
    assert pantalla.actualizar() == ("error_red_social", "Cancelaste el inicio de sesión")


def test_si_se_cae_el_servidor(ventana):
    pantalla = pantalla_esperando(ventana, ClienteFalso(error="No se pudo conectar con el servidor"))
    assert pantalla.actualizar() == ("error_red_social", "No se pudo conectar con el servidor")


def test_cancelar_vuelve_al_login(ventana):
    pantalla = pantalla_esperando(ventana, ClienteFalso())
    assert pantalla.manejar_evento(clic(pantalla.boton_cancelar)) == ("ir_a_login", None)


def test_abrir_otra_vez(ventana, navegador):
    pantalla = pantalla_esperando(ventana, ClienteFalso())
    pantalla.manejar_evento(clic(pantalla.boton_abrir))
    assert navegador == [INICIO["url"]]


def test_tab_no_falla_sin_campos(ventana):
    pantalla = pantalla_esperando(ventana, ClienteFalso())
    pantalla.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, unicode="\t"))
    pantalla.mostrar_error("algo")
    pantalla.dibujar()


def test_cliente_guarda_el_token_cuando_esta_listo(monkeypatch):
    cliente = ClienteAPI("http://backend-falso")
    monkeypatch.setattr(
        cliente, "_enviar", lambda *a: {"estado": "listo", "access_token": "tok", "jugador": {}}
    )
    cliente.revisar_login_social("espera-123")
    assert cliente.token == "tok"


def test_cliente_no_guarda_token_si_esta_pendiente(monkeypatch):
    cliente = ClienteAPI("http://backend-falso")
    monkeypatch.setattr(cliente, "_enviar", lambda *a: {"estado": "pendiente"})
    cliente.revisar_login_social("espera-123")
    assert cliente.token is None
