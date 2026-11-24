"""Pruebas del botón Jugar: abre el juego de la arena y vuelve al menú."""
import sys

import pygame

import juego


def test_jugar_abre_el_juego_de_la_arena(ventana, monkeypatch):
    llamadas = []
    monkeypatch.setattr(juego.subprocess, "run", lambda comando, cwd: llamadas.append((comando, cwd)))

    nueva = juego.iniciar_partida(ventana, cliente=None, jugador={"nombre_usuario": "ana_07"})

    comando, carpeta = llamadas[0]
    assert comando == [sys.executable, str(juego.RUTA_JUEGO)]
    assert carpeta == juego.RUTA_JUEGO.parent
    assert nueva.get_size() == (900, 700)  # el menú vuelve con el mismo tamaño


def test_el_juego_esta_en_la_carpeta_principal():
    assert juego.RUTA_JUEGO.name == "Logica_ReactorControl.py"
    assert juego.RUTA_JUEGO.exists()


def test_si_falta_el_juego_muestra_un_aviso(ventana, monkeypatch, tmp_path):
    monkeypatch.setattr(juego, "RUTA_JUEGO", tmp_path / "no-existe.py")
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, unicode=" "))

    assert juego.iniciar_partida(ventana, None, {"nombre_usuario": "ana_07"}) is ventana
