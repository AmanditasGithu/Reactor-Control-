"""Pruebas de la pantalla para verificar el correo (US-003), con un backend falso."""
import pygame

from cliente_api import ErrorAPI
from pantallas_cuentas import PantallaLogin, PantallaVerificarCorreo


class ClienteFalso:
    def __init__(self, error=None, codigo_error=None):
        self.error = error
        self.codigo_error = codigo_error
        self.llamadas = []

    def verificar_correo(self, correo, codigo):
        self.llamadas.append(("verificar", correo, codigo))
        if self.error:
            raise ErrorAPI(self.error, self.codigo_error)
        return {"mensaje": "ok"}

    def reenviar_verificacion(self, correo):
        self.llamadas.append(("reenviar", correo))
        return {"mensaje": "ok"}

    def iniciar_sesion(self, usuario_o_correo, contrasena):
        raise ErrorAPI(self.error, self.codigo_error)


def escribir(campo, texto):
    campo.activo = True
    for letra in texto:
        campo.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=letra))
    campo.activo = False


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boton.rect.center)


def test_el_correo_llega_escrito_y_el_cursor_en_el_codigo(ventana):
    pantalla = PantallaVerificarCorreo(ventana, ClienteFalso(), "ana@correo.com")
    assert pantalla.campo_correo.texto == "ana@correo.com"
    assert pantalla.campo_codigo.activo


def test_verificar_envia_correo_y_codigo(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaVerificarCorreo(ventana, cliente, "ana@correo.com")
    escribir(pantalla.campo_codigo, "123456")

    assert pantalla.enviar() == ("correo_verificado", "ana@correo.com")
    assert cliente.llamadas == [("verificar", "ana@correo.com", "123456")]


def test_codigo_incorrecto_muestra_error(ventana):
    pantalla = PantallaVerificarCorreo(ventana, ClienteFalso("El código es incorrecto o ya venció"), "a@b.com")
    escribir(pantalla.campo_codigo, "000000")

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "El código es incorrecto o ya venció"


def test_sin_codigo_no_se_envia(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaVerificarCorreo(ventana, cliente, "a@b.com")

    assert pantalla.enviar() is None
    assert cliente.llamadas == []


def test_reenviar_pide_otro_codigo(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaVerificarCorreo(ventana, cliente, "ana@correo.com")

    assert pantalla.manejar_evento(clic(pantalla.boton_reenviar)) is None
    assert cliente.llamadas == [("reenviar", "ana@correo.com")]
    assert pantalla.mensaje == "Te enviamos un código nuevo"


def test_mas_tarde_vuelve_al_login(ventana):
    pantalla = PantallaVerificarCorreo(ventana, ClienteFalso(), "a@b.com")
    assert pantalla.manejar_evento(clic(pantalla.boton_despues)) == ("ir_a_login", None)


def test_login_sin_verificar_lleva_a_verificar(ventana):
    cliente = ClienteFalso("Verificá tu correo antes de iniciar sesión", 403)
    pantalla = PantallaLogin(ventana, cliente)
    escribir(pantalla.campo_usuario, "ana@correo.com")
    escribir(pantalla.campo_contrasena, "clave-segura-1")

    assert pantalla.enviar() == ("ir_a_verificar", "ana@correo.com")


def test_la_pantalla_se_dibuja(ventana):
    pantalla = PantallaVerificarCorreo(ventana, ClienteFalso(), "a@b.com")
    pantalla.mostrar_exito("¡Cuenta creada! Te enviamos un código a tu correo")
    pantalla.dibujar()
