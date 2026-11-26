"""Sala de partidas: elegir jugar solo o multijugador antes de abrir la arena.

Multijugador: una jugadora crea la partida (y elige el escenario) y les pasa el número
a las demás, que se unen con ese número. Con 2 o más, cualquiera toca "Iniciar".
La partida la lleva el servidor de partidas (Logica-juego-backend, puerto 8002), el
mismo que usa la versión para celular, así que también se puede jugar compu contra celular.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

import pygame

from cliente_api import API_URL
from componentes import BLANCO, CIAN, DORADO, FONDO, GRIS, PANEL, ROJO, VERDE, Boton, CampoTexto

ESCENARIOS = [
    ("planta_industrial", "Planta industrial"),
    ("laboratorio_subterraneo", "Laboratorio subterráneo"),
    ("complejo_militar", "Complejo militar"),
]
NOMBRES_ESCENARIO = dict(ESCENARIOS)


def direccion_servidor_partidas() -> str:
    """host:puerto del servidor de partidas. Por defecto, la misma compu del backend, puerto 8002."""
    configurada = os.getenv("REACTOR_PARTIDAS_URL")
    if configurada:
        return configurada.removeprefix("http://").removeprefix("https://").rstrip("/")
    host = urlparse(API_URL).hostname or "127.0.0.1"
    return f"{host}:8002"


class ErrorPartidas(Exception):
    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


def llamar(metodo: str, ruta: str, datos: dict | None = None):
    """Llamada al servidor de partidas (HTTP con JSON)."""
    url = f"http://{direccion_servidor_partidas()}{ruta}"
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    peticion = urllib.request.Request(url, data=cuerpo, method=metodo)
    if cuerpo is not None:
        peticion.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(peticion, timeout=3) as respuesta:
            return json.loads(respuesta.read() or b"null")
    except urllib.error.HTTPError as error:
        try:
            detalle = json.loads(error.read()).get("detail")
        except Exception:
            detalle = None
        raise ErrorPartidas(str(detalle or f"Error {error.code}"), error.code) from None
    except (urllib.error.URLError, OSError):
        raise ErrorPartidas("No se pudo conectar con el servidor de partidas (puerto 8002). ¿Está encendido?") from None


class SalaMultijugador:
    def __init__(self, ventana, jugador: dict):
        self.ventana = ventana
        self.jugador = jugador
        ancho, alto = ventana.get_size()
        self.x = ancho // 2 - 210
        self.ancho = 420
        self.paso = "modo"
        self.mensaje = ""
        self.error = True
        self.id_partida = None
        self.escenario = ESCENARIOS[0][0]
        self.partida = None
        self.ultima_revision = 0.0

        self.fuente_titulo = pygame.font.SysFont("Arial", 34, bold=True)
        self.fuente = pygame.font.SysFont("Arial", 20)
        self.fuente_chica = pygame.font.SysFont("Arial", 16)

        y = 170
        self.boton_solo = Boton(self.x, y, self.ancho, "Jugar solo")
        self.boton_multi = Boton(self.x, y + 60, self.ancho, "Multijugador", principal=False)
        self.boton_volver = Boton(self.x, alto - 90, self.ancho, "Volver al menú", principal=False)

        self.botones_escenario = [
            Boton(self.x, 175 + i * 52, self.ancho, nombre, principal=False)
            for i, (clave, nombre) in enumerate(ESCENARIOS)
        ]
        self.marcar_escenario()
        self.boton_crear = Boton(self.x, 340, self.ancho, "Crear partida")
        self.campo_numero = CampoTexto(self.x, 450, 250, "Número de partida", largo_maximo=6)
        self.boton_unirse = Boton(self.x + 265, 450, self.ancho - 265, "Unirme", principal=False)

        self.boton_iniciar = Boton(self.x, alto - 150, self.ancho, "Iniciar partida")
        self.boton_salir = Boton(self.x, alto - 90, self.ancho, "Salir de la sala", principal=False)

    def marcar_escenario(self):
        """El escenario elegido se ve con borde y una marca; los demás, apagados."""
        for boton, (clave, nombre) in zip(self.botones_escenario, ESCENARIOS):
            boton.principal = False
            boton.texto = f"»  {nombre}  «" if clave == self.escenario else nombre

    # ---------- acciones ----------
    def avisar(self, texto, error=True):
        self.mensaje, self.error = texto, error

    def unirse(self, numero: int) -> None:
        datos = {"id_jugador": int(self.jugador["id"]), "nombre": str(self.jugador.get("nombre_usuario", "Jugador"))}
        try:
            llamar("POST", f"/partidas/{numero}/unirse", datos)
        except ErrorPartidas as error:
            if error.codigo == 404:
                return self.avisar(f"No existe la partida {numero}")
            if error.codigo == 409 and not self.ya_estoy_en(numero):
                return self.avisar("Esa partida ya empezó o terminó")
            if error.codigo not in (409,):
                return self.avisar(str(error))
        self.id_partida = numero
        self.paso = "espera"
        self.avisar("")
        self.revisar_sala(forzar=True)

    def ya_estoy_en(self, numero: int) -> bool:
        try:
            partida = llamar("GET", f"/partidas/{numero}")
        except ErrorPartidas:
            return False
        return any(j["id_jugador"] == self.jugador["id"] for j in partida.get("jugadores", []))

    def crear(self) -> None:
        try:
            nueva = llamar("POST", "/partidas", {"escenario": self.escenario})
        except ErrorPartidas as error:
            return self.avisar(str(error))
        self.unirse(nueva["id_partida"])

    def revisar_sala(self, forzar=False) -> None:
        """Pregunta cada segundo quién está en la sala y si ya empezó."""
        if not forzar and time.monotonic() - self.ultima_revision < 1.0:
            return
        self.ultima_revision = time.monotonic()
        try:
            self.partida = llamar("GET", f"/partidas/{self.id_partida}")
        except ErrorPartidas as error:
            self.avisar(str(error))

    def iniciar(self) -> None:
        try:
            llamar("POST", f"/partidas/{self.id_partida}/iniciar")
        except ErrorPartidas as error:
            return self.avisar("Se necesitan al menos 2 jugadores" if error.codigo == 409 else str(error))
        self.revisar_sala(forzar=True)

    def resultado_si_empezo(self):
        if self.paso == "espera" and self.partida and self.partida.get("estado") == "JUGANDO":
            return {
                "id_partida": self.id_partida,
                "escenario": self.partida.get("escenario") or ESCENARIOS[0][0],
                "direccion": direccion_servidor_partidas(),
            }
        return None

    # ---------- eventos ----------
    def manejar_evento(self, evento):
        """Devuelve "solo", "volver" o None (sigue en la sala)."""
        if self.paso == "modo":
            if self.boton_solo.fue_presionado(evento):
                return "solo"
            if self.boton_multi.fue_presionado(evento):
                self.paso = "multi"
            elif self.boton_volver.fue_presionado(evento):
                return "volver"
        elif self.paso == "multi":
            self.campo_numero.manejar_evento(evento)
            for boton, (clave, _) in zip(self.botones_escenario, ESCENARIOS):
                if boton.fue_presionado(evento):
                    self.escenario = clave
                    self.marcar_escenario()
            if self.boton_crear.fue_presionado(evento):
                self.crear()
            elif self.boton_unirse.fue_presionado(evento) or (
                    evento.type == pygame.KEYDOWN and evento.key == pygame.K_RETURN and self.campo_numero.activo):
                texto = self.campo_numero.texto.strip()
                if texto.isdigit() and int(texto) > 0:
                    self.unirse(int(texto))
                else:
                    self.avisar("Escribí el número de la partida")
            elif self.boton_volver.fue_presionado(evento):
                self.paso, self.mensaje = "modo", ""
        elif self.paso == "espera":
            if self.boton_iniciar.fue_presionado(evento):
                self.iniciar()
            elif self.boton_salir.fue_presionado(evento):
                self.paso, self.id_partida, self.partida, self.mensaje = "multi", None, None, ""
        return None

    # ---------- dibujo ----------
    def titulo(self, texto, y=90):
        superficie = self.fuente_titulo.render(texto, True, DORADO)
        self.ventana.blit(superficie, superficie.get_rect(center=(self.ventana.get_width() // 2, y)))

    def texto(self, texto, y, color=GRIS, fuente=None):
        superficie = (fuente or self.fuente).render(texto, True, color)
        self.ventana.blit(superficie, superficie.get_rect(center=(self.ventana.get_width() // 2, y)))

    def dibujar(self):
        self.ventana.fill(FONDO)
        if self.paso == "modo":
            self.titulo("¿Cómo querés jugar?")
            self.boton_solo.dibujar(self.ventana, self.fuente)
            self.boton_multi.dibujar(self.ventana, self.fuente)
            self.texto("Multijugador: varias compus (o celulares) en la misma partida", 300, GRIS, self.fuente_chica)
            self.boton_volver.dibujar(self.ventana, self.fuente)
        elif self.paso == "multi":
            self.titulo("Multijugador")
            self.texto("Elegí el escenario y creá una partida nueva", 140, GRIS, self.fuente_chica)
            for boton in self.botones_escenario:
                boton.dibujar(self.ventana, self.fuente)
            self.boton_crear.dibujar(self.ventana, self.fuente)
            self.texto("— o unite a la partida de otra persona —", 405, GRIS, self.fuente_chica)
            self.campo_numero.dibujar(self.ventana, self.fuente, self.fuente_chica)
            self.boton_unirse.dibujar(self.ventana, self.fuente)
            self.boton_volver.dibujar(self.ventana, self.fuente)
        elif self.paso == "espera":
            self.titulo(f"Partida {self.id_partida}")
            escenario = NOMBRES_ESCENARIO.get((self.partida or {}).get("escenario"), "Planta industrial")
            self.texto(f"Escenario: {escenario}", 135, CIAN)
            self.texto("Pasale este número a los demás jugadores", 165, GRIS, self.fuente_chica)
            jugadores = (self.partida or {}).get("jugadores", [])
            for i, j in enumerate(jugadores[:6]):
                caja = pygame.Rect(self.x, 200 + i * 46, self.ancho, 38)
                pygame.draw.rect(self.ventana, PANEL, caja, border_radius=5)
                nombre = j["nombre"] + ("  (vos)" if j["id_jugador"] == self.jugador["id"] else "")
                superficie = self.fuente.render(nombre, True, BLANCO)
                self.ventana.blit(superficie, (caja.x + 14, caja.y + 8))
            faltan = max(0, 2 - len(jugadores))
            self.boton_iniciar.texto = f"Falta {faltan} jugador para iniciar" if faltan else "Iniciar partida"
            self.boton_iniciar.principal = not faltan
            self.boton_iniciar.dibujar(self.ventana, self.fuente)
            self.boton_salir.dibujar(self.ventana, self.fuente)
        if self.mensaje:
            self.texto(self.mensaje[:80], self.ventana.get_height() - 30, ROJO if self.error else VERDE, self.fuente_chica)


def elegir_partida(ventana, jugador: dict):
    """Devuelve "solo", None (volver al menú) o los datos de la partida multijugador que empezó."""
    reloj = pygame.time.Clock()
    sala = SalaMultijugador(ventana, jugador)
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                return None
            accion = sala.manejar_evento(evento)
            if accion == "solo":
                return "solo"
            if accion == "volver":
                return None
        if sala.paso == "espera":
            sala.revisar_sala()
            empezada = sala.resultado_si_empezo()
            if empezada:
                return empezada
        sala.dibujar()
        pygame.display.flip()
        reloj.tick(30)
