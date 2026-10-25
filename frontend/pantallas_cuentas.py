"""Pantallas de inicio de sesión (US-004) y registro (US-001) en Pygame.

Uso desde el juego:
    cliente, jugador = ejecutar_pantallas_cuentas(ventana)
    # cliente.token  -> el pase de sesión para hablar con el backend
    # jugador        -> {"id", "nombre_usuario", "correo", ...}

Para probarlas solas:  python pantallas_cuentas.py   (con el backend encendido)
"""
import sys

import pygame

from cliente_api import ClienteAPI, ErrorAPI
from componentes import BLANCO, CIAN, DORADO, FONDO, GRIS, PANEL, ROJO, VERDE, Boton, CampoTexto

ANCHO_PANEL = 420


class Pantalla:
    """Lo común de las dos pantallas: título, campos, botones y mensaje."""

    titulo = ""

    def __init__(self, ventana, cliente: ClienteAPI):
        self.ventana = ventana
        self.cliente = cliente
        self.mensaje = ""
        self.color_mensaje = ROJO
        self.fuente_titulo = pygame.font.SysFont("Arial", 34, bold=True)
        self.fuente = pygame.font.SysFont("Arial", 20)
        self.fuente_chica = pygame.font.SysFont("Arial", 16)
        ancho, alto = ventana.get_size()
        self.x = (ancho - ANCHO_PANEL) // 2
        self.y_inicio = alto // 2 - 200
        self.campos: list[CampoTexto] = []
        self.botones: list[Boton] = []

    def mostrar_error(self, texto: str) -> None:
        self.mensaje, self.color_mensaje = texto, ROJO

    def mostrar_exito(self, texto: str) -> None:
        self.mensaje, self.color_mensaje = texto, VERDE

    def pasar_al_siguiente_campo(self) -> None:
        """Tab mueve el cursor al siguiente campo."""
        actual = next((i for i, c in enumerate(self.campos) if c.activo), -1)
        for campo in self.campos:
            campo.activo = False
        self.campos[(actual + 1) % len(self.campos)].activo = True

    def manejar_evento(self, evento):
        """Devuelve una acción para el ciclo principal, o None si no pasa nada."""
        for campo in self.campos:
            campo.manejar_evento(evento)
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_TAB:
            self.pasar_al_siguiente_campo()
        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN:
            return self.enviar()
        return self.revisar_botones(evento)

    def revisar_botones(self, evento):
        return None

    def enviar(self):
        return None

    def dibujar(self) -> None:
        self.ventana.fill(FONDO)
        ancho_ventana = self.ventana.get_width()
        y_panel = self.y_inicio - 30
        alto_panel = self.botones[-1].rect.bottom + 30 - y_panel  # el panel llega hasta el último botón
        panel = pygame.Rect(self.x - 30, y_panel, ANCHO_PANEL + 60, alto_panel)
        pygame.draw.rect(self.ventana, PANEL, panel, border_radius=10)
        pygame.draw.rect(self.ventana, DORADO, panel, 2, border_radius=10)

        nombre_juego = self.fuente_chica.render("CONTROL DEL REACTOR", True, CIAN)
        self.ventana.blit(nombre_juego, nombre_juego.get_rect(center=(ancho_ventana // 2, self.y_inicio)))
        titulo = self.fuente_titulo.render(self.titulo, True, BLANCO)
        self.ventana.blit(titulo, titulo.get_rect(center=(ancho_ventana // 2, self.y_inicio + 38)))

        for campo in self.campos:
            campo.dibujar(self.ventana, self.fuente, self.fuente_chica)
        for boton in self.botones:
            boton.dibujar(self.ventana, self.fuente)

        if self.mensaje:
            texto = self.fuente_chica.render(self.mensaje, True, self.color_mensaje)
            y_mensaje = self.campos[-1].rect.bottom + 16
            self.ventana.blit(texto, texto.get_rect(center=(ancho_ventana // 2, y_mensaje)))


class PantallaLogin(Pantalla):
    """US-004: iniciar sesión con usuario (o correo) y contraseña."""

    titulo = "Iniciar sesión"

    def __init__(self, ventana, cliente):
        super().__init__(ventana, cliente)
        y = self.y_inicio + 110
        self.campo_usuario = CampoTexto(self.x, y, ANCHO_PANEL, "Usuario o correo")
        self.campo_contrasena = CampoTexto(self.x, y + 75, ANCHO_PANEL, "Contraseña", oculto=True)
        self.campos = [self.campo_usuario, self.campo_contrasena]
        self.boton_entrar = Boton(self.x, y + 175, ANCHO_PANEL, "Entrar")
        self.boton_registro = Boton(self.x, y + 233, ANCHO_PANEL, "Crear una cuenta", principal=False)
        self.botones = [self.boton_entrar, self.boton_registro]
        self.campo_usuario.activo = True

    def revisar_botones(self, evento):
        if self.boton_entrar.fue_presionado(evento):
            return self.enviar()
        if self.boton_registro.fue_presionado(evento):
            return ("ir_a_registro", None)
        return None

    def enviar(self):
        usuario = self.campo_usuario.texto.strip()
        contrasena = self.campo_contrasena.texto
        if not usuario or not contrasena:
            self.mostrar_error("Completá todos los campos")
            return None
        try:
            jugador = self.cliente.iniciar_sesion(usuario, contrasena)
        except ErrorAPI as error:
            self.mostrar_error(error.mensaje)
            self.campo_contrasena.texto = ""
            return None
        return ("sesion_iniciada", jugador)


class PantallaRegistro(Pantalla):
    """US-001: crear una cuenta con usuario, correo y contraseña."""

    titulo = "Crear cuenta"

    def __init__(self, ventana, cliente):
        super().__init__(ventana, cliente)
        self.y_inicio -= 60
        y = self.y_inicio + 110
        self.campo_usuario = CampoTexto(self.x, y, ANCHO_PANEL, "Nombre de usuario", largo_maximo=30)
        self.campo_correo = CampoTexto(self.x, y + 75, ANCHO_PANEL, "Correo")
        self.campo_contrasena = CampoTexto(self.x, y + 150, ANCHO_PANEL, "Contraseña (mínimo 8)", oculto=True)
        self.campo_confirmar = CampoTexto(self.x, y + 225, ANCHO_PANEL, "Confirmar contraseña", oculto=True)
        self.campos = [self.campo_usuario, self.campo_correo, self.campo_contrasena, self.campo_confirmar]
        self.boton_crear = Boton(self.x, y + 325, ANCHO_PANEL, "Crear cuenta")
        self.boton_volver = Boton(self.x, y + 383, ANCHO_PANEL, "Ya tengo cuenta", principal=False)
        self.botones = [self.boton_crear, self.boton_volver]
        self.campo_usuario.activo = True

    def revisar_botones(self, evento):
        if self.boton_crear.fue_presionado(evento):
            return self.enviar()
        if self.boton_volver.fue_presionado(evento):
            return ("ir_a_login", None)
        return None

    def enviar(self):
        if not all(campo.texto.strip() for campo in self.campos):
            self.mostrar_error("Completá todos los campos")
            return None
        if self.campo_contrasena.texto != self.campo_confirmar.texto:
            self.mostrar_error("Las contraseñas no coinciden")
            return None
        try:
            jugador = self.cliente.registrar(
                self.campo_usuario.texto.strip(),
                self.campo_correo.texto.strip(),
                self.campo_contrasena.texto,
            )
        except ErrorAPI as error:
            self.mostrar_error(error.mensaje)
            return None
        return ("cuenta_creada", jugador)


def ejecutar_pantallas_cuentas(ventana, cliente: ClienteAPI | None = None):
    """Muestra login y registro hasta que el jugador inicia sesión.

    Devuelve (cliente, jugador). El cliente ya tiene guardado el token.
    """
    cliente = cliente or ClienteAPI()
    reloj = pygame.time.Clock()
    pantalla = PantallaLogin(ventana, cliente)

    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT or (
                evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE
            ):
                pygame.quit()
                sys.exit()

            accion = pantalla.manejar_evento(evento)
            if accion is None:
                continue
            tipo, jugador = accion
            if tipo == "ir_a_registro":
                pantalla = PantallaRegistro(ventana, cliente)
            elif tipo == "ir_a_login":
                pantalla = PantallaLogin(ventana, cliente)
            elif tipo == "cuenta_creada":
                pantalla = PantallaLogin(ventana, cliente)
                pantalla.campo_usuario.texto = jugador["nombre_usuario"]
                pantalla.campo_usuario.activo = False
                pantalla.campo_contrasena.activo = True
                pantalla.mostrar_exito("¡Cuenta creada! Ahora iniciá sesión")
            elif tipo == "sesion_iniciada":
                return cliente, jugador

        pantalla.dibujar()
        pygame.display.flip()
        reloj.tick(60)


if __name__ == "__main__":
    pygame.init()
    ventana = pygame.display.set_mode((900, 700))
    pygame.display.set_caption("Control del Reactor")
    _, jugador = ejecutar_pantallas_cuentas(ventana)

    # Pantalla de bienvenida provisional, hasta conectar con la arena
    fuente = pygame.font.SysFont("Arial", 32, bold=True)
    while True:
        for evento in pygame.event.get():
            if evento.type in (pygame.QUIT, pygame.KEYDOWN):
                pygame.quit()
                sys.exit()
        ventana.fill(FONDO)
        texto = fuente.render(f"¡Bienvenido, {jugador['nombre_usuario']}!", True, DORADO)
        ventana.blit(texto, texto.get_rect(center=(450, 330)))
        ayuda = pygame.font.SysFont("Arial", 18).render("Presioná cualquier tecla para salir", True, GRIS)
        ventana.blit(ayuda, ayuda.get_rect(center=(450, 380)))
        pygame.display.flip()
