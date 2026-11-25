"""Pinta el marcador del servidor sobre la arena Pygame existente (US-017)."""

import math
import pygame


FONDO = (13, 19, 32, 226)
BLANCO = (244, 248, 255)
GRIS = (169, 188, 207)
VERDE = (57, 208, 166)
AMARILLO = (244, 192, 80)


def dibujar_hud_marcador(superficie, datos, id_local=None):
    """HUD de solo lectura: no altera posiciones ni estado del juego."""
    ancho_pantalla = superficie.get_width()
    ancho = min(395, ancho_pantalla - 24)
    jugadores = list(datos.get("jugadores") or [])[:4]
    tiene_reactor = bool(datos.get("reactor"))
    alto = 112 + len(jugadores) * 30 + (34 if tiene_reactor else 0) + 68
    panel = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    panel.fill(FONDO)
    pygame.draw.rect(panel, (90, 114, 145), panel.get_rect(), 1, border_radius=9)
    font = pygame.font.SysFont("Arial", 17, bold=True)
    pequeno = pygame.font.SysFont("Arial", 14)

    def texto(contenido, x, y, color=BLANCO, fuente=font):
        panel.blit(fuente.render(str(contenido), True, color), (x, y))

    conexion = datos.get("conexion", "DESCONECTADO")
    conectado = conexion == "CONECTADO"
    texto("US-017  |  MARCADOR EN VIVO", 12, 9, BLANCO)
    texto(conexion, ancho - 124, 11, VERDE if conectado else AMARILLO, pequeno)
    if datos.get("id_partida") is not None:
        texto(f"Partida {datos['id_partida']}  ·  {datos.get('estado') or 'ESPERANDO'}", 12, 33, GRIS, pequeno)
    else:
        texto("Esperando datos del servidor...", 12, 33, GRIS, pequeno)
    meta = datos.get("meta") or 0
    if meta:
        texto(f"Meta: {meta} puntos", 12, 51, GRIS, pequeno)
    tiempo = datos.get("tiempo_restante")
    if isinstance(tiempo, (int, float)):
        segundos = max(0, math.ceil(tiempo))
        texto(f"Tiempo: {segundos // 60:02d}:{segundos % 60:02d}", ancho - 119, 51, GRIS, pequeno)

    for i, jugador in enumerate(jugadores):
        y = 76 + i * 30
        nombre = str(jugador.get("nombre", "Jugador"))[:17]
        puntos = int(jugador.get("puntos", 0))
        local = jugador.get("id_jugador") == id_local
        texto(f"{i+1}. {nombre}", 12, y, VERDE if local else BLANCO, pequeno)
        texto(f"{puntos} pts", ancho - 91, y, AMARILLO, pequeno)
        if meta > 0:
            pygame.draw.rect(panel, (55, 64, 80), (12, y + 18, ancho - 24, 5), border_radius=2)
            pygame.draw.rect(panel, VERDE, (12, y + 18, max(0, round((ancho - 24) * min(1, puntos / meta))), 5), border_radius=2)

    reactor = datos.get("reactor") or {}
    if reactor:
        y = 80 + len(jugadores) * 30
        energia = reactor.get("energia_actual", 0)
        maxima = max(1, reactor.get("energia_maxima", 1))
        texto(f"Reactor: {energia}/{maxima}", 12, y, GRIS, pequeno)
        pygame.draw.rect(panel, (55, 64, 80), (12, y + 19, ancho - 24, 7), border_radius=3)
        pygame.draw.rect(panel, AMARILLO, (12, y + 19, max(0, round((ancho-24)*min(1,energia/maxima))), 7), border_radius=3)

    # US-012: mostrar la bonificación en la UI, sin inventar un mapeo
    # de coordenadas lógicas a píxeles de la arena local.
    bonus = datos.get('bonificacion_disponible')
    y_bonus = 82 + len(jugadores) * 30 + (35 if tiene_reactor else 0)
    if bonus:
        texto(f"BONO x{bonus.get('multiplicador', 2)} DISPONIBLE", 12, y_bonus, AMARILLO, pequeno)
        texto(f"Casilla ({bonus.get('x')}, {bonus.get('y')}) - {bonus.get('segundos_restantes', 0)}s", 12, y_bonus + 17, GRIS, pequeno)
    else:
        texto("Sin bono en el mapa", 12, y_bonus, GRIS, pequeno)
    activos = [
        j for j in jugadores if (j.get('bonificacion') or {}).get('segundos_restantes', 0) > 0
    ]
    if activos:
        j = activos[0]
        efecto = j['bonificacion']
        texto(
            f"{str(j.get('nombre', 'Jugador'))[:13]}: x{efecto.get('multiplicador', 2)} "
            f"({efecto.get('segundos_restantes', 0)}s)",
            12, y_bonus + 36, VERDE, pequeno
        )
    superficie.blit(panel, (12, 10))
