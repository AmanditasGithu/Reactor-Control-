"""Celdas de energía de la arena (US-011).

Aparecen en pasillos libres del mapa. Cuando el jugador pasa por encima de una,
la recoge, suma puntos y aparece otra en un lugar libre al azar.

Uso desde el juego:
    celdas = GestorCeldas(matriz_mapa, TAMANO_CELDA, OFFSET_X, OFFSET_Y)
    ...
    celdas.actualizar(jugador.rect)   # en cada cuadro, después de mover al jugador
    celdas.dibujar(ventana)           # después de dibujar el mapa
    celdas.dibujar_marcador(ventana)  # al final, para que quede encima
"""
import math
import random

import pygame

CANTIDAD_CELDAS = 4  # celdas en el mapa al mismo tiempo
PUNTOS_POR_CELDA = 10
COLOR_CELDA = (255, 215, 0)  # dorado
COLOR_BRILLO = (255, 245, 170)


def posiciones_libres(matriz: list[str]) -> list[tuple[int, int]]:
    """(fila, columna) de cada pasillo libre (' ') del mapa: ahí pueden aparecer celdas."""
    return [
        (fila_idx, col_idx)
        for fila_idx, fila in enumerate(matriz)
        for col_idx, caracter in enumerate(fila)
        if caracter == " "
    ]


class CeldaEnergia:
    """Una celda de energía: un círculo dorado más chico que una casilla del mapa."""

    def __init__(self, fila: int, columna: int, tamano: int, offset_x: int, offset_y: int):
        self.fila = fila
        self.columna = columna
        margen = tamano // 4
        self.rect = pygame.Rect(
            offset_x + columna * tamano + margen,
            offset_y + fila * tamano + margen,
            tamano - 2 * margen,
            tamano - 2 * margen,
        )

    def dibujar(self, superficie) -> None:
        # Late suavemente para que se note en el mapa
        latido = (math.sin(pygame.time.get_ticks() / 200) + 1) / 2  # entre 0 y 1
        radio = max(2, self.rect.width // 2)
        pygame.draw.circle(superficie, COLOR_CELDA, self.rect.center, radio + int(2 * latido))
        pygame.draw.circle(superficie, COLOR_BRILLO, self.rect.center, max(1, radio // 2))


class GestorCeldas:
    """Crea las celdas, revisa si el jugador recoge alguna y lleva los puntos."""

    def __init__(self, matriz, tamano, offset_x, offset_y, cantidad=CANTIDAD_CELDAS, azar=None):
        self.tamano = tamano
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.libres = posiciones_libres(matriz)
        self.azar = azar or random.Random()
        self.celdas: list[CeldaEnergia] = []
        self.puntos = 0
        self.recogidas = 0
        for _ in range(min(cantidad, len(self.libres))):
            self.celdas.append(self._nueva_celda())

    def _nueva_celda(self, evitar=None) -> CeldaEnergia:
        """Una celda en un pasillo libre que no tenga otra celda ni esté debajo de `evitar`."""
        ocupadas = {(c.fila, c.columna) for c in self.celdas}
        candidatas = [p for p in self.libres if p not in ocupadas]
        self.azar.shuffle(candidatas)
        for fila, columna in candidatas:
            celda = CeldaEnergia(fila, columna, self.tamano, self.offset_x, self.offset_y)
            if evitar is None or not celda.rect.colliderect(evitar):
                return celda
        fila, columna = candidatas[0]  # mapa casi lleno: se usa la primera libre
        return CeldaEnergia(fila, columna, self.tamano, self.offset_x, self.offset_y)

    def actualizar(self, rect_jugador) -> int:
        """Recoge las celdas que toca el jugador. Devuelve los puntos ganados en este cuadro."""
        ganados = 0
        for celda in list(self.celdas):
            if rect_jugador.colliderect(celda.rect):
                self.celdas.remove(celda)
                self.celdas.append(self._nueva_celda(evitar=rect_jugador))
                self.recogidas += 1
                self.puntos += PUNTOS_POR_CELDA
                ganados += PUNTOS_POR_CELDA
        return ganados

    def dibujar(self, superficie) -> None:
        for celda in self.celdas:
            celda.dibujar(superficie)

    def dibujar_marcador(self, superficie) -> None:
        """Puntos y celdas recogidas, arriba a la izquierda."""
        fuente = pygame.font.SysFont("Arial", 20, bold=True)
        texto = fuente.render(
            f"Puntos: {self.puntos}    Celdas: {self.recogidas}", True, (255, 255, 255)
        )
        fondo = texto.get_rect(topleft=(20, 16)).inflate(20, 10)
        pygame.draw.rect(superficie, (40, 45, 60), fondo, border_radius=5)
        pygame.draw.rect(superficie, COLOR_CELDA, fondo, 2, border_radius=5)
        superficie.blit(texto, (20, 16))
