"""Punto de entrada del juego: login → menú → arena (Logica_ReactorControl.py).

Para probar:  python juego.py   (con el backend encendido)
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pygame

from cliente_api import ClienteAPI
from componentes import FONDO, GRIS, DORADO
from pantallas_cuentas import ejecutar_pantallas_cuentas
from pantallas_menu import ejecutar_menu
from sala_multijugador import elegir_partida


# El juego de la arena (mapa, guardianes y ceremonia) está en la carpeta principal del repo
RUTA_JUEGO = Path(__file__).resolve().parent.parent / "Arenas" / "Logica_ReactorControl.py"


def iniciar_partida(ventana, cliente: ClienteAPI, jugador: dict, multijugador: dict | None = None):
    """Abre el juego de la arena y, al cerrarlo (ESC), vuelve al menú.

    Por ahora el juego corre como un programa aparte. Devuelve la ventana del menú,
    porque se vuelve a crear al regresar.
    """
    if not RUTA_JUEGO.exists():
        mostrar_aviso(ventana, "No se encontró Logica_ReactorControl.py")
        return ventana

    tamano = ventana.get_size()
    # La arena escribe aquí cada partida que termina, para guardarla después en el ranking
    nombre = "".join(c for c in str(jugador.get("nombre_usuario", "jugador")) if c.isalnum() or c in "-_")
    archivo = Path(tempfile.gettempdir()) / f"reactor_resultados_{nombre}.jsonl"
    entorno = dict(os.environ, REACTOR_ARCHIVO_RESULTADO=str(archivo),
                   REACTOR_NOMBRE_JUGADOR=str(jugador.get("nombre_usuario", "")))
    if multijugador:
        # La arena se conecta a la partida compartida; el resultado lo guarda el servidor de partidas
        entorno.update(
            REACTOR_PARTIDA_ID=str(multijugador["id_partida"]),
            REACTOR_JUGADOR_ID=str(jugador["id"]),
            REACTOR_ESCENARIO=str(multijugador["escenario"]),
            REACTOR_PARTIDAS_WS=str(multijugador["direccion"]),
        )
    pygame.display.iconify()  # minimiza el menú mientras se juega
    subprocess.run([sys.executable, str(RUTA_JUEGO)], cwd=RUTA_JUEGO.parent, env=entorno)
    ventana = pygame.display.set_mode(tamano)  # vuelve a mostrar el menú
    pygame.event.clear()  # descarta las teclas presionadas durante el juego
    mensaje = guardar_resultados(cliente, archivo)
    if mensaje:
        mostrar_aviso(ventana, mensaje)
    return ventana


def guardar_resultados(cliente: ClienteAPI, archivo: Path) -> str | None:
    """Manda al backend las partidas que terminaron, para el perfil y el ranking.

    Las que no se pudieron guardar (backend apagado, sesión vencida...) quedan en el
    archivo y se vuelven a intentar la próxima vez que se juegue.
    """
    if not archivo.exists():
        return None  # salió antes de terminar una partida
    guardadas, puntos, pendientes, motivo = 0, 0, [], ""
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            datos = json.loads(linea)
        except ValueError:
            continue  # línea dañada: no se puede recuperar
        try:
            cliente.guardar_partida_local(datos)
            guardadas += 1
            puntos += int(datos.get("puntos", 0))
        except Exception as error:  # sin conexión, sesión vencida, backend sin actualizar...
            pendientes.append(linea)
            motivo = str(error)
    if pendientes:
        archivo.write_text("\n".join(pendientes) + "\n", encoding="utf-8")
    else:
        archivo.unlink(missing_ok=True)
    if pendientes and not guardadas:
        return f"No se pudo guardar la partida: {motivo}"[:60]
    texto = f"Partida guardada: +{puntos} puntos" if guardadas == 1 else f"{guardadas} partidas guardadas: +{puntos} puntos"
    return texto + (f" ({len(pendientes)} pendiente)" if pendientes else "")


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
            eleccion = elegir_partida(ventana, jugador)  # solo o multijugador
            if eleccion is None:
                continue  # volvió al menú
            multijugador = eleccion if isinstance(eleccion, dict) else None
            ventana = iniciar_partida(ventana, cliente, jugador, multijugador)
        # Si cerró sesión, vuelve al login


if __name__ == "__main__":
    main()
