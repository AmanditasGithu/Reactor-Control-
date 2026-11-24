"""Menú principal, perfil del jugador (US-006) y ranking global (US-022) en Pygame.

Uso desde el juego:
    accion = ejecutar_menu(ventana, cliente, jugador)
    # accion es "jugar" o "cerrar_sesion"
"""
import sys

import pygame

from cliente_api import ClienteAPI, ErrorAPI
from componentes import BLANCO, CIAN, DORADO, FONDO, GRIS, PANEL, ROJO, Boton

ANCHO_PANEL = 420


def dibujar_marco(ventana, rect: pygame.Rect) -> None:
    pygame.draw.rect(ventana, PANEL, rect, border_radius=10)
    pygame.draw.rect(ventana, DORADO, rect, 2, border_radius=10)


def dibujar_centrado(ventana, fuente, texto, color, y) -> None:
    superficie = fuente.render(texto, True, color)
    ventana.blit(superficie, superficie.get_rect(center=(ventana.get_width() // 2, y)))


class PantallaMenu:
    """Menú principal: Jugar, Mi perfil, Ranking y Cerrar sesión."""

    def __init__(self, ventana, jugador: dict):
        self.ventana = ventana
        self.jugador = jugador
        self.fuente_titulo = pygame.font.SysFont("Arial", 34, bold=True)
        self.fuente = pygame.font.SysFont("Arial", 20)
        self.fuente_chica = pygame.font.SysFont("Arial", 16)
        ancho, alto = ventana.get_size()
        self.x = (ancho - ANCHO_PANEL) // 2
        self.y_inicio = alto // 2 - 190
        y = self.y_inicio + 110
        self.boton_jugar = Boton(self.x, y, ANCHO_PANEL, "Jugar")
        self.boton_perfil = Boton(self.x, y + 60, ANCHO_PANEL, "Mi perfil", principal=False)
        self.boton_ranking = Boton(self.x, y + 120, ANCHO_PANEL, "Ranking", principal=False)
        self.boton_salir = Boton(self.x, y + 180, ANCHO_PANEL, "Cerrar sesión", principal=False)
        self.botones = [self.boton_jugar, self.boton_perfil, self.boton_ranking, self.boton_salir]

    def manejar_evento(self, evento):
        if self.boton_jugar.fue_presionado(evento):
            return "jugar"
        if self.boton_perfil.fue_presionado(evento):
            return "ir_a_perfil"
        if self.boton_ranking.fue_presionado(evento):
            return "ir_a_ranking"
        if self.boton_salir.fue_presionado(evento):
            return "cerrar_sesion"
        return None

    def dibujar(self) -> None:
        self.ventana.fill(FONDO)
        dibujar_marco(
            self.ventana,
            pygame.Rect(self.x - 30, self.y_inicio - 30, ANCHO_PANEL + 60, self.boton_salir.rect.bottom + 30 - (self.y_inicio - 30)),
        )
        dibujar_centrado(self.ventana, self.fuente_chica, "CONTROL DEL REACTOR", CIAN, self.y_inicio)
        dibujar_centrado(self.ventana, self.fuente_titulo, "Menú principal", BLANCO, self.y_inicio + 38)
        dibujar_centrado(self.ventana, self.fuente_chica, f"Jugador: {self.jugador['nombre_usuario']}", GRIS, self.y_inicio + 76)
        for boton in self.botones:
            boton.dibujar(self.ventana, self.fuente)


class PantallaConDatos:
    """Base del perfil y el ranking: piden datos al backend una vez y tienen botón Volver."""

    titulo = ""

    def __init__(self, ventana, cliente: ClienteAPI):
        self.ventana = ventana
        self.cliente = cliente
        self.fuente_titulo = pygame.font.SysFont("Arial", 34, bold=True)
        self.fuente = pygame.font.SysFont("Arial", 20)
        self.fuente_chica = pygame.font.SysFont("Arial", 16)
        ancho, alto = ventana.get_size()
        self.ancho_panel = min(640, ancho - 40)
        self.x = (ancho - self.ancho_panel) // 2
        self.y_inicio = max(40, alto // 2 - 270)
        self.boton_volver = Boton(self.x, self.y_inicio + 470, self.ancho_panel, "Volver al menú", principal=False)
        self.error = ""
        self.datos = None
        try:
            self.datos = self.cargar()
        except ErrorAPI as error:
            self.error = error.mensaje

    def cargar(self):
        raise NotImplementedError

    def manejar_evento(self, evento):
        volver = evento.type == pygame.KEYDOWN and evento.key == pygame.K_BACKSPACE
        if volver or self.boton_volver.fue_presionado(evento):
            return "volver"
        return None

    def dibujar(self) -> None:
        self.ventana.fill(FONDO)
        alto = self.boton_volver.rect.bottom + 30 - (self.y_inicio - 30)
        dibujar_marco(self.ventana, pygame.Rect(self.x - 30, self.y_inicio - 30, self.ancho_panel + 60, alto))
        dibujar_centrado(self.ventana, self.fuente_chica, "CONTROL DEL REACTOR", CIAN, self.y_inicio)
        dibujar_centrado(self.ventana, self.fuente_titulo, self.titulo, BLANCO, self.y_inicio + 38)
        if self.error:
            dibujar_centrado(self.ventana, self.fuente, self.error, ROJO, self.y_inicio + 220)
        else:
            self.dibujar_contenido()
        self.boton_volver.dibujar(self.ventana, self.fuente)

    def dibujar_contenido(self) -> None:
        raise NotImplementedError

    def texto(self, contenido, x, y, color=BLANCO, fuente=None) -> None:
        self.ventana.blit((fuente or self.fuente).render(str(contenido), True, color), (x, y))


class PantallaPerfil(PantallaConDatos):
    """US-006: datos, estadísticas, historial y récords del jugador."""

    titulo = "Mi perfil"

    def cargar(self):
        return self.cliente.obtener_perfil()

    def dibujar_contenido(self) -> None:
        p = self.datos
        x, y = self.x, self.y_inicio + 80
        self.texto(p["nombre_usuario"], x, y, DORADO, self.fuente_titulo)
        self.texto(p["correo"], x, y + 42, GRIS, self.fuente_chica)

        # Estadísticas en cuatro columnas
        estadisticas = [
            ("Puntos", p["puntos_totales"]),
            ("Victorias", p["victorias"]),
            ("Partidas", p["partidas_jugadas"]),
            ("Ranking", f"#{p['posicion_ranking']}"),
        ]
        ancho_columna = self.ancho_panel // 4
        for i, (nombre, valor) in enumerate(estadisticas):
            cx = x + i * ancho_columna
            self.texto(valor, cx, y + 80, BLANCO, self.fuente_titulo)
            self.texto(nombre, cx, y + 120, GRIS, self.fuente_chica)

        record = next((r["valor"] for r in p["records"] if r["tipo"] == "mayor_puntuacion"), None)
        self.texto(f"Mejor puntuación: {record if record is not None else '—'}", x, y + 160, CIAN)

        self.texto("Últimas partidas", x, y + 200, GRIS, self.fuente_chica)
        if not p["historial"]:
            self.texto("Todavía no has jugado partidas.", x, y + 226, GRIS)
        for i, partida in enumerate(p["historial"][:5]):
            lugar = f"{partida['posicion']}.º lugar" if partida["posicion"] else "sin posición"
            self.texto(f"Partida {partida['partida_id']}  ·  {partida['puntos']} pts  ·  {lugar}", x, y + 226 + i * 28)


class PantallaRanking(PantallaConDatos):
    """US-022: top 10 histórico de jugadores."""

    titulo = "Ranking global"

    def cargar(self):
        return self.cliente.obtener_ranking(10)

    def dibujar_contenido(self) -> None:
        x, y = self.x, self.y_inicio + 85
        columnas = [("#", 0), ("Jugador", 50), ("Puntos", 330), ("Victorias", 430), ("Partidas", 540)]
        for nombre, dx in columnas:
            self.texto(nombre, x + dx, y, GRIS, self.fuente_chica)
        if not self.datos:
            self.texto("Todavía no hay jugadores en el ranking.", x, y + 34, GRIS)
        for i, fila in enumerate(self.datos):
            fy = y + 30 + i * 34
            color = DORADO if fila["posicion"] == 1 else BLANCO
            valores = [fila["posicion"], fila["nombre_usuario"], fila["puntos_totales"], fila["victorias"], fila["partidas_jugadas"]]
            for (_, dx), valor in zip(columnas, valores):
                self.texto(valor, x + dx, fy, color)


def ejecutar_menu(ventana, cliente: ClienteAPI, jugador: dict) -> str:
    """Muestra el menú hasta que el jugador elige Jugar o Cerrar sesión.

    Devuelve "jugar" o "cerrar_sesion".
    """
    reloj = pygame.time.Clock()
    pantalla = PantallaMenu(ventana, jugador)

    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()

            accion = pantalla.manejar_evento(evento)
            if accion == "ir_a_perfil":
                pantalla = PantallaPerfil(ventana, cliente)
            elif accion == "ir_a_ranking":
                pantalla = PantallaRanking(ventana, cliente)
            elif accion == "volver":
                pantalla = PantallaMenu(ventana, jugador)
            elif accion == "cerrar_sesion":
                cliente.cerrar_sesion()
                return "cerrar_sesion"
            elif accion == "jugar":
                return "jugar"

        pantalla.dibujar()
        pygame.display.flip()
        reloj.tick(60)
