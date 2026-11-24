import time
import math
from datetime import datetime, timezone
from uuid import uuid4

from modelos.Reactor import Reactor
from modelos.Terminal import Terminal


class Partida:

    def __init__(self, id_partida, duracion= 180, meta= 100):
        if duracion <= 0 or meta <= 0:
            raise ValueError('La duración y la meta deben sier positivas')
        
        self.id_partida = id_partida
        # UUID único: evita colisiones si el servidor se reinicia y la numeración vuelve a 1.
        self.id_externo = uuid4().hex
        self.fecha_inicio_utc = None
        self.fecha_fin_utc = None
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

        # US-012: un coleccionable visible a la vez, sin acumular multiplicadores.
        self.bonificacion_disponible = None
        self.proxima_bonificacion = None
        self.siguiente_id_bonificacion = 1
        self.indice_posicion_bonificacion = 0
        self.espera_inicial_bonificacion = 8.0
        self.intervalo_bonificaciones = 15.0
        self.tiempo_en_mapa_bonificacion = 12.0
        self.duracion_efecto_bonificacion = 8.0

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
        self.fecha_inicio_utc = datetime.now(timezone.utc).isoformat()
        self.proxima_bonificacion = self.inicio_monotonico + self.espera_inicial_bonificacion
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
        self.fecha_fin_utc = datetime.now(timezone.utc).isoformat()
        
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