"""Punto de entrada del juego: login → menú → arena (Logica_ReactorControl.py).

Para probar:  python juego.py   (con el backend encendido)
"""
import subprocess
import sys
from pathlib import Path

import pygame

from cliente_api import ClienteAPI
from componentes import FONDO, GRIS, DORADO
from pantallas_cuentas import ejecutar_pantallas_cuentas
from pantallas_menu import ejecutar_menu


# El juego de la arena (mapa, guardianes y ceremonia) está en la carpeta principal del repo
RUTA_JUEGO = Path(__file__).resolve().parent.parent / "Logica_ReactorControl.py"


def iniciar_partida(ventana, cliente: ClienteAPI, jugador: dict):
    """Abre el juego de la arena y, al cerrarlo (ESC), vuelve al menú.

    Por ahora el juego corre como un programa aparte. Devuelve la ventana del menú,
    porque se vuelve a crear al regresar.
    """
    if not RUTA_JUEGO.exists():
        mostrar_aviso(ventana, "No se encontró Logica_ReactorControl.py")
        return ventana

    tamano = ventana.get_size()
    pygame.display.iconify()  # minimiza el menú mientras se juega
    subprocess.run([sys.executable, str(RUTA_JUEGO)], cwd=RUTA_JUEGO.parent)
    ventana = pygame.display.set_mode(tamano)  # vuelve a mostrar el menú
    pygame.event.clear()  # descarta las teclas presionadas durante el juego
    return ventana


def mostrar_aviso(ventana, mensaje: str) -> None:
    """Pantalla de aviso; cualquier tecla vuelve al menú."""
    fuente = pygame.font.SysFont("Arial", 24, bold=True)
    chica = pygame.font.SysFont("Arial", 18)
    centro = ventana.get_width() // 2, ventana.get_height() // 2
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                raise SystemExit
            if evento.type == pygame.KEYDOWN:
                return
        ventana.fill(FONDO)
        texto = fuente.render(mensaje, True, DORADO)
        ventana.blit(texto, texto.get_rect(center=centro))
        ayuda = chica.render("Presioná cualquier tecla para volver al menú", True, GRIS)
        ventana.blit(ayuda, ayuda.get_rect(center=(centro[0], centro[1] + 45)))
        pygame.display.flip()


def main() -> None:
    pygame.init()
    ventana = pygame.display.set_mode((900, 700))
    pygame.display.set_caption("Control del Reactor")
    cliente = ClienteAPI()

    while True:
        cliente, jugador = ejecutar_pantallas_cuentas(ventana, cliente)
        while ejecutar_menu(ventana, cliente, jugador) == "jugar":
            ventana = iniciar_partida(ventana, cliente, jugador)
        # Si cerró sesión, vuelve al login


if __name__ == "__main__":
    main()
