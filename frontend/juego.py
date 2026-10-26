"""Punto de entrada del juego: login → menú → arena.

Para probar:  python juego.py   (con el backend encendido)
"""
import pygame

from cliente_api import ClienteAPI
from componentes import FONDO, GRIS, DORADO
from pantallas_cuentas import ejecutar_pantallas_cuentas
from pantallas_menu import ejecutar_menu


def iniciar_partida(ventana, cliente: ClienteAPI, jugador: dict) -> None:
    """AQUÍ SE CONECTA LA ARENA (US-007).

    Reemplazar esta pantalla provisional por la función que arranca la partida.
    `cliente.token` sirve para hablar con el backend como este jugador.
    """
    fuente = pygame.font.SysFont("Arial", 28, bold=True)
    chica = pygame.font.SysFont("Arial", 18)
    centro = ventana.get_width() // 2, ventana.get_height() // 2
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                raise SystemExit
            if evento.type == pygame.KEYDOWN:
                return
        ventana.fill(FONDO)
        texto = fuente.render(f"Aquí empieza la arena, {jugador['nombre_usuario']}", True, DORADO)
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
            iniciar_partida(ventana, cliente, jugador)
        # Si cerró sesión, vuelve al login


if __name__ == "__main__":
    main()
