import time
import math

from modelos.Reactor import Reactor
from modelos.Terminal import Terminal


class Partida:

    def __init__(self, id_partida, duracion= 180, meta= 100):
        if duracion <= 0 or meta <= 0:
            raise ValueError('La duración y la meta deben sier positivas')
        
        self.id_partida = id_partida
        self.jugadores = []
        self.reactor = Reactor()
        self.terminales = [
            Terminal(
                id_terminal=1,
                x=2,
                y=2,
                puntos=10
            ), Terminal(
                id_terminal=2,
                x=8,
                y=8,
                puntos=10
            )
        ]
        self.duracion = float(duracion)
        self.meta = int(meta)
        self.inicio_monotonico = None
        self.tiempo_restante_final = None
        self.motivo_fin = None
        self.resultados_finales = None
        self.ultimo_segundo_notificado = None

        self.estado = "ESPERANDO"
    
    def agregar_jugador(self, jugador):
        if self.estado != "ESPERANDO":
            return False
        
        for participante in self.jugadores:
            if participante.id_jugador == jugador.id_jugador:
                return False
        
        self.jugadores.append(jugador)
        return True
    
    def iniciar_partida(self):
        if len(self.jugadores) < 2:
            return False
        
        if self.estado != "ESPERANDO":
            return False
        
        self.estado = "JUGANDO"
        self.inicio_monotonico = time.monotonic()
        self.ultimo_segundo_notificado = math.ceil(self.duracion)
        
        return True

    def tiempo_restante(self, ahora=None):
        if self.estado == 'ESPERANDO':
            return self.duracion
        
        if self.estado == 'FINALIZADA':
            return self.tiempo_restante_final
        
        if ahora is None:
            ahora = time.monotonic()
        
        return max(0.0, self.duracion - (ahora - self.inicio_monotonico))

    def finalizar_si_corresponde(self, ahora=None):
        if self.estado != 'JUGANDO':
            return False
        
        if ahora is None:
            ahora = time.monotonic()
    
        if self.tiempo_restante(ahora) <= 0:
            motivo = 'TIEMPO'
        
        elif any(j.puntos >= self.meta for j in self.jugadores):
            motivo = 'PUNTUACION'
        
        else:
            return False
    
        self.tiempo_restante_final = self.tiempo_restante(ahora)
        self.motivo_fin = motivo
        self.estado = 'FINALIZADA'
        
        for jugador in self.jugadores:
            jugador.extrayendo = False
    
        self.resultados_finales = [
            {'id_jugador': j.id_jugador,
             'nombre': j.nombre,
             'puntos': j.puntos}
             for j in sorted(
                 self.jugadores, 
                 key=lambda j: (
                     -j.puntos, j.id_jugador
                     )
            )
        ]
        
        return True
    
    def obtener_jugadores(self):
        return self.jugadores