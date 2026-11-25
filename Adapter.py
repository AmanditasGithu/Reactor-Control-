#Se utilizara el patron adapter para adecuar la interfaz backend del Sprint 2 y la interfaz grafica del juego y su logica
import sys 
import os 
RUTA_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Logica-juego-backend"))
if RUTA_BACKEND not in sys.path:
    sys.path.append(RUTA_BACKEND)

from modelos.Partida import Partida #type: ignore 
from modelos.Jugador import Jugador as JugadorLogico #type: ignore 


class AdaptadorEstadoBackend:

    def __init__(self, offset_x, offset_y, tamano_celda):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.tamano_celda = tamano_celda

    def celda_a_pixeles(self, col, fila):
        px = self.offset_x + (col * self.tamano_celda)
        py = self.offset_y + (fila * self.tamano_celda)
        return px, py

    def pixeles_a_celda(self, px, py):
        col = round((px - self.offset_x) / self.tamano_celda)
        fila = round((py - self.offset_y) / self.tamano_celda)
        return col, fila
    
    def crear_partida_integrada(self, col_reactor, fila_reactor, coords_terminales):
        partida = Partida(id_partida=1, duracion=180, meta=100)
        partida.reactor.x = col_reactor
        partida.reactor.y = fila_reactor

    
        for i, (cx, cy) in enumerate(coords_terminales):
            if i < len(partida.terminales):
                partida.terminales[i].x = cx
                partida.terminales[i].y = cy

        j_azul = JugadorLogico(1, "AZUL")
        j_naranja = JugadorLogico(2, "NARANJA")
        j_naranja.x, j_naranja.y = 4, 3
        j_verde = JugadorLogico(3, "VERDE")
        j_verde.x, j_verde.y = 6, 5

        partida.agregar_jugador(j_azul)
        partida.agregar_jugador(j_naranja)
        partida.agregar_jugador(j_verde)
        partida.iniciar_partida()
        return partida, j_azul

    def sincronizar_jugador(self, jugador_pygame, jugador_logico):
        col, fila = self.pixeles_a_celda(jugador_pygame.rect.x, jugador_pygame.rect.y)
        jugador_logico.x = col
        jugador_logico.y = fila

    def adaptar_jugadores_arena(self, jugadores_data):

        adaptados = []
        for j in jugadores_data:
            px, py = self.celda_a_pixeles(j["x"], j["y"])
            adaptados.append({
                "id_jugador": j.get("id_jugador"),
                "nombre": j.get("nombre", "JUGADOR"),
                "px": px,
                "py": py,
                "puntos": j.get("puntos", 0),
                "extrayendo": j.get("extrayendo", False),
            })
        return adaptados

    def adaptar_resultados_victoria(self, resultados_finales):
        if not resultados_finales:
            return "Azul", []

        ganador = resultados_finales[0]["nombre"].capitalize()
        datos_ui = []
        for r in resultados_finales:
            datos_ui.append({
                "nombre": r["nombre"].upper(),
                "puntos": r["puntos"],
                "energia": r.get("energia", r["puntos"]),
                "celdas": r.get("celdas", 0),
                "golpes_sufridos": r.get("golpes_sufridos",0),
                "vida": r.get("vida", 100),
            })
        return ganador, datos_ui