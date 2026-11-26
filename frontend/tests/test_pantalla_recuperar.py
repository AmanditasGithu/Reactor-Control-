"""Pruebas de las pantallas para recuperar la contraseña (US-005), con un backend falso."""
import pygame

from cliente_api import ErrorAPI
from pantallas_cuentas import PantallaLogin, PantallaNuevaContrasena, PantallaPedirCodigo


class ClienteFalso:
    def __init__(self, error=None):
        self.error = error
        self.llamadas = []

    def solicitar_recuperacion(self, correo):
        self.llamadas.append(("solicitar", correo))
        if self.error:
            raise ErrorAPI(self.error)
        return {"mensaje": "ok"}

    def restablecer_contrasena(self, correo, codigo, contrasena_nueva):
        self.llamadas.append(("restablecer", correo, codigo, contrasena_nueva))
        if self.error:
            raise ErrorAPI(self.error)
        return {"mensaje": "ok"}


def escribir(campo, texto):
    campo.activo = True
    for letra in texto:
        campo.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=letra))
    campo.activo = False


def clic(boton):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=boton.rect.center)


def test_login_tiene_boton_olvide_mi_contrasena(ventana):
    pantalla = PantallaLogin(ventana, ClienteFalso())
    assert pantalla.manejar_evento(clic(pantalla.boton_olvide)) == ("ir_a_recuperar", None)


def test_pedir_codigo_envia_el_correo(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaPedirCodigo(ventana, cliente)
    escribir(pantalla.campo_correo, "ana@correo.com")

    assert pantalla.enviar() == ("codigo_enviado", "ana@correo.com")
    assert cliente.llamadas == [("solicitar", "ana@correo.com")]


def test_pedir_codigo_sin_correo_muestra_error(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaPedirCodigo(ventana, cliente)

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "Escribí tu correo"
    assert cliente.llamadas == []


def test_nueva_contrasena_envia_codigo_y_contrasena(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaNuevaContrasena(ventana, cliente, "ana@correo.com")
    escribir(pantalla.campo_codigo, "123456")
    escribir(pantalla.campo_contrasena, "clave-nueva-1")
    escribir(pantalla.campo_confirmar, "clave-nueva-1")

    assert pantalla.enviar() == ("contrasena_cambiada", "ana@correo.com")
    assert cliente.llamadas == [("restablecer", "ana@correo.com", "123456", "clave-nueva-1")]


def test_contrasenas_distintas_no_se_envian(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaNuevaContrasena(ventana, cliente, "ana@correo.com")
    escribir(pantalla.campo_codigo, "123456")
    escribir(pantalla.campo_contrasena, "clave-nueva-1")
    escribir(pantalla.campo_confirmar, "otra-cosa-22")

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "Las contraseñas no coinciden"
    assert cliente.llamadas == []


def test_codigo_incorrecto_muestra_el_error_del_backend(ventana):
    pantalla = PantallaNuevaContrasena(ventana, ClienteFalso("El código es incorrecto o ya venció"), "a@b.com")
    escribir(pantalla.campo_codigo, "000000")
    escribir(pantalla.campo_contrasena, "clave-nueva-1")
    escribir(pantalla.campo_confirmar, "clave-nueva-1")

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "El código es incorrecto o ya venció"


def test_el_codigo_acepta_maximo_6_caracteres(ventana):
    pantalla = PantallaNuevaContrasena(ventana, ClienteFalso(), "a@b.com")
    escribir(pantalla.campo_codigo, "12345678")
    assert pantalla.campo_codigo.texto == "123456"


def test_las_pantallas_se_dibujan(ventana):
    for pantalla in (
        PantallaLogin(ventana, ClienteFalso()),
        PantallaPedirCodigo(ventana, ClienteFalso()),
        PantallaNuevaContrasena(ventana, ClienteFalso(), "a@b.com"),
    ):
        pantalla.mostrar_error("prueba")
        pantalla.dibujar()
