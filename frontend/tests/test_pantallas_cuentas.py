"""Pruebas de las pantallas de login y registro, con un backend falso."""
import pygame

from cliente_api import ErrorAPI
from componentes import CampoTexto
from pantallas_cuentas import PantallaLogin, PantallaRegistro


class ClienteFalso:
    """Reemplaza al backend: guarda lo que le mandan y responde lo que le digamos."""

    def __init__(self, error=None):
        self.error = error
        self.llamadas = []

    def registrar(self, nombre_usuario, correo, contrasena):
        self.llamadas.append(("registrar", nombre_usuario, correo, contrasena))
        if self.error:
            raise ErrorAPI(self.error)
        return {"id": 1, "nombre_usuario": nombre_usuario, "correo": correo}

    def iniciar_sesion(self, usuario_o_correo, contrasena):
        self.llamadas.append(("iniciar_sesion", usuario_o_correo, contrasena))
        if self.error:
            raise ErrorAPI(self.error)
        return {"id": 1, "nombre_usuario": "ana_07"}


def tecla(unicode="", key=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


def escribir(campo, texto):
    campo.activo = True
    for letra in texto:
        campo.manejar_evento(tecla(letra))
    campo.activo = False


def llenar_registro(pantalla, contrasena="clave-segura-1", confirmar="clave-segura-1"):
    escribir(pantalla.campo_usuario, "ana_07")
    escribir(pantalla.campo_correo, "ana@correo.com")
    escribir(pantalla.campo_contrasena, contrasena)
    escribir(pantalla.campo_confirmar, confirmar)


def test_campo_de_texto_escribe_y_borra(ventana):
    campo = CampoTexto(0, 0, 200, "Prueba")
    escribir(campo, "hola")
    campo.activo = True
    campo.manejar_evento(tecla(key=pygame.K_BACKSPACE))
    assert campo.texto == "hol"


def test_campo_inactivo_no_escribe(ventana):
    campo = CampoTexto(0, 0, 200, "Prueba")
    campo.manejar_evento(tecla("a"))
    assert campo.texto == ""


def test_campo_respeta_largo_maximo(ventana):
    campo = CampoTexto(0, 0, 200, "Prueba", largo_maximo=3)
    escribir(campo, "abcdef")
    assert campo.texto == "abc"


def test_tab_pasa_al_siguiente_campo(ventana):
    pantalla = PantallaLogin(ventana, ClienteFalso())
    pantalla.manejar_evento(tecla(key=pygame.K_TAB))
    assert pantalla.campo_contrasena.activo
    assert not pantalla.campo_usuario.activo


def test_login_exitoso_devuelve_el_jugador(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaLogin(ventana, cliente)
    escribir(pantalla.campo_usuario, "ana_07")
    escribir(pantalla.campo_contrasena, "clave-segura-1")

    accion = pantalla.enviar()
    assert accion[0] == "sesion_iniciada"
    assert cliente.llamadas == [("iniciar_sesion", "ana_07", "clave-segura-1")]


def test_login_con_campos_vacios_no_llama_al_backend(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaLogin(ventana, cliente)

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "Completá todos los campos"
    assert cliente.llamadas == []


def test_login_incorrecto_muestra_error_y_borra_contrasena(ventana):
    pantalla = PantallaLogin(ventana, ClienteFalso(error="Usuario, correo o contraseña incorrectos"))
    escribir(pantalla.campo_usuario, "ana_07")
    escribir(pantalla.campo_contrasena, "mala")

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "Usuario, correo o contraseña incorrectos"
    assert pantalla.campo_contrasena.texto == ""


def test_registro_exitoso(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaRegistro(ventana, cliente)
    llenar_registro(pantalla)

    assert pantalla.enviar()[0] == "cuenta_creada"
    assert cliente.llamadas == [("registrar", "ana_07", "ana@correo.com", "clave-segura-1")]


def test_registro_con_contrasenas_distintas_no_llama_al_backend(ventana):
    cliente = ClienteFalso()
    pantalla = PantallaRegistro(ventana, cliente)
    llenar_registro(pantalla, confirmar="otra-clave")

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "Las contraseñas no coinciden"
    assert cliente.llamadas == []


def test_registro_muestra_error_del_backend(ventana):
    pantalla = PantallaRegistro(ventana, ClienteFalso(error="Ese correo ya está registrado"))
    llenar_registro(pantalla)

    assert pantalla.enviar() is None
    assert pantalla.mensaje == "Ese correo ya está registrado"


def test_las_pantallas_se_dibujan_sin_errores(ventana):
    PantallaLogin(ventana, ClienteFalso()).dibujar()
    PantallaRegistro(ventana, ClienteFalso()).dibujar()
