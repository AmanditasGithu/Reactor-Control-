"""Pruebas de las celdas de energía de la arena (US-011)."""
import random
import sys
from pathlib import Path

import pygame

# celdas_energia.py está en la carpeta principal del repo, junto al juego
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from celdas_energia import PUNTOS_POR_CELDA, GestorCeldas, posiciones_libres  # noqa: E402

MAPA = [
    "#######",
    "#  T  #",
    "# # R #",
    "#     #",
    "#######",
]
TAMANO = 20


def gestor(cantidad=3, semilla=1):
    return GestorCeldas(MAPA, TAMANO, 0, 0, cantidad=cantidad, azar=random.Random(semilla))


def rect_de(fila, columna):
    return pygame.Rect(columna * TAMANO, fila * TAMANO, TAMANO, TAMANO)


def test_solo_se_usan_pasillos_libres():
    libres = posiciones_libres(MAPA)
    assert (1, 1) in libres and (3, 5) in libres
    assert (0, 0) not in libres  # pared
    assert (1, 3) not in libres  # trampa
    assert (2, 4) not in libres  # reactor


def test_se_crean_las_celdas_en_lugares_distintos():
    celdas = gestor(cantidad=4).celdas
    posiciones = {(c.fila, c.columna) for c in celdas}
    assert len(celdas) == 4
    assert len(posiciones) == 4
    assert posiciones <= set(posiciones_libres(MAPA))


def test_al_tocar_una_celda_suma_puntos_y_aparece_otra():
    g = gestor()
    celda = g.celdas[0]

    ganados = g.actualizar(rect_de(celda.fila, celda.columna))

    assert ganados == PUNTOS_POR_CELDA
    assert g.puntos == PUNTOS_POR_CELDA
    assert g.recogidas == 1
    assert len(g.celdas) == 3  # se repone
    assert celda not in g.celdas


def test_la_celda_nueva_no_aparece_debajo_del_jugador():
    g = gestor()
    jugador = rect_de(g.celdas[0].fila, g.celdas[0].columna)
    for _ in range(20):
        g.actualizar(jugador)
        assert not any(c.rect.colliderect(jugador) for c in g.celdas)


def test_sin_tocar_celdas_no_suma():
    g = gestor()
    lejos = pygame.Rect(-100, -100, TAMANO, TAMANO)
    assert g.actualizar(lejos) == 0
    assert g.puntos == 0


def test_la_celda_es_mas_chica_que_la_casilla():
    celda = gestor().celdas[0]
    assert celda.rect.width < TAMANO
    assert rect_de(celda.fila, celda.columna).contains(celda.rect)


def test_se_dibujan_las_celdas_y_el_marcador(ventana):
    g = gestor()
    g.dibujar(ventana)
    g.dibujar_marcador(ventana)
