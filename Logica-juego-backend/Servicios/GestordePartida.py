import time 
import math

from threading import RLock
#from modelos.Partida#
import Partida

class GestordePartida:
    TIEMPO_MAX_SIN_LATIDO = 1.5

    def __init__(self):
        self.partidas = {}
        self.siguiente_id = 1
        self.bloqueo = RLock()
    
    def crear_partida(self):
        with self.bloqueo:
            partida = Partida(self.siguiente_id)
            self.partidas[self.siguiente_id] = partida
            self.siguiente_id += 1
            return partida
    
    def obtener_partida(self, id_partida):
        with self.bloqueo:
            return self.partidas.get(id_partida)
    
    def unir_jugador(self, id_partida, jugador):
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            return partida.agregar_jugador(jugador) if partida else False
        
    def iniciar_partida(self, id_partida):
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            return partida.iniciar_partida() if partida else False
    
    def listar_partidas(self):
        with self.bloqueo:
            return [
                {'id_partida': p.id_partida,
                 'estado': p.estado,
                 'cantidad_jugadores': len(p.jugadores)}
                for p in self.partidas.values()
            ]

    def _verificar_fin(self, partida, ahora=None):
        if partida.finalizar_si_corresponde(ahora):
            self._eventos_finalizacion.append(
                (partida.id_partida, self._estado(partida))
            )
        
            return True
        
        return False

    def consumir_finalizaciones(self):
        with self.bloqueo:
            eventos = self._eventos_finalizacion
            self._eventos_finalizacion = []
            return eventos

    def _jugador(self, partida, id_jugador):
        for jugador in partida.jugadores:
            if jugador.id_jugador == id_jugador:
                return jugador
        return None

    def jugador_en_partida(self, id_partida, id_jugador):
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            return bool(partida and self._jugador(partida, id_jugador))

    def _estado(self, partida, ahora= None):
        return {
            'id_partida': partida.id_partida,
            'estado': partida.estado,
            'duracion': partida.duracion,
            'puntuacion_objetivo': partida.meta,
            'tiempo_restante': round(partida.tiempo_restante(ahora), 2),
            'motivo_fin': partida.motivo_fin,
            'resultados_finales': partida.resultados_finales,
            'jugadores': [
                {'id_jugador': j.id_jugador, 'nombre': j.nombre,
                 'x': j.x, 'y': j.y, 'puntos': j.puntos,
                 'extrayendo': j.extrayendo}
                for j in partida.jugadores
            ],
            'reactor': partida.reactor.obtener_estado(),
            'terminales': [
                terminal.obtener_estado() for terminal in partida.terminales
            ]
        }

    def obtener_estado(self, id_partida):
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            if not partida:
                return None
            self._verificar_fin(partida)
            return self._estado(partida)
        
    def mover_jugador_detallado(self, id_partida, id_jugador, direccion):
        if direccion not in {'ARRIBA', 'ABAJO', 'IZQUIERDA', 'DERECHA'}:
            return {'ok': False, 'terminal_activada': None}
        
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            
            if not partida or partida.estado != 'JUGANDO':
                return {'ok': False, 'terminal_activada': None}
            self._verificar_fin(partida)

            if partida.estado != 'JUGANDO':
                return {'ok': False, 'terminal_activada': None}
            
            jugador = self._jugador(partida, id_jugador)
            
            if not jugador or jugador.extrayendo:
                return {'ok': False, 'terminal_activada': None}
            
            jugador.mover(direccion)

            terminal_activada = None
            
            for terminal in partida.terminales:
                if terminal.activar(jugador):
                    terminal_activada = {
                        'id_terminal': terminal.id_terminal,
                        'id_jugador': jugador.id_jugador,
                        'puntos_obtenidos': terminal.puntos
                    }
                    
                    break

            self._verificar_fin(partida)
            return {
                'ok': True,
                'terminal_activada': terminal_activada,
                'estado': self._estado(partida),
            }
    
    def mover_jugador(self, id_partida, id_jugador, direccion):
        resultado = self.mover_jugador_detallado(
            id_partida, id_jugador, direccion
        )
        return resultado['ok']
    
    def procesar_senal_accion(self, id_partida, id_jugador, senal):
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            if not partida:
                return {'ok': False, 'cambio': False, 'mensaje': 'Partida no activa'}
            self._verificar_fin(partida)
            if partida.estado != 'JUGANDO':
                return {'ok': False, 'cambio': False, 'mensaje': 'Partida no activa'}
            jugador = self._jugador(partida, id_jugador)
            if not jugador:
                return {'ok': False, 'cambio': False, 'mensaje': 'Jugador no encontrado'}
        
            ahora = time.monotonic()
            if senal == 'ACCION_SOLTAR':
                cambio = jugador.extrayendo
                jugador.extrayendo = False
                return {'ok': True, 'cambio': cambio, 'mensaje': 'Extracción detenida'}
        
            if senal == 'ACCION_LATIDO':
                if not jugador.extrayendo:
                    return {'ok': False, 'cambio': False, 'mensaje': 'No está extrayendo'}
                if ahora - jugador.ultimo_latido_accion > self.TIEMPO_MAX_SIN_LATIDO:
                    jugador.extrayendo = False
                    return {'ok': False, 'cambio': True, 'mensaje': 'Extracción caducada'}
                jugador.ultimo_latido_accion = ahora
                
                return {'ok': True, 'cambio': False, 'mensaje': 'Latido recibido'}
        
            if senal != 'ACCION_PRESIONAR':
                return {'ok': False, 'cambio': False, 'mensaje': 'Señal no válida'}
            if jugador.extrayendo:
                return {'ok': False, 'cambio': False, 'mensaje': 'Ya está extrayendo'}
        
            reactor = partida.reactor
            if not reactor.jugador_cerca(jugador):
                return {'ok': False, 'cambio': False, 'mensaje': 'Fuera de rango'}
            if reactor.energia_actual <= 0:
                return {'ok': False, 'cambio': False, 'mensaje': 'Reactor sin energía'}
        
            jugador.extrayendo = True
            jugador.ultimo_latido_accion = ahora
            jugador.ultimo_ciclo_extraccion = ahora
            cantidad = reactor.extraer(jugador, ahora)
            if reactor.energia_actual == 0:
                jugador.extrayendo = False
                self._verificar_fin(partida, ahora)
                return {
                    'ok': True,
                    'cambio': True,
                    'mensaje': f'Extraídas {cantidad} unidades de energía',
                }

    def procesar_extracciones(self):
        cambios = []
        with self.bloqueo:
            ahora = time.monotonic()
            for partida in self.partidas.values():
                if self._verificar_fin(partida, ahora):
                    cambios.append((partida.id_partida, self._estado(partida, ahora)))
                    continue
                if partida.estado != 'JUGANDO':
                    continue

                reactor = partida.reactor
                cambio = reactor.recargar_si_corresponde(ahora)
                for jugador in partida.jugadores:
                    if not jugador.extrayendo:
                        continue
                    if (ahora - jugador.ultimo_latido_accion > self.TIEMPO_MAX_SIN_LATIDO
                            or not reactor.jugador_cerca(jugador)
                            or reactor.energia_actual <= 0):
                        jugador.extrayendo = False
                        cambio = True
                        continue
                    if ahora - jugador.ultimo_ciclo_extraccion < reactor.intervalo:
                        continue
                    cantidad = reactor.extraer(jugador, ahora)
                    jugador.ultimo_ciclo_extraccion = ahora
                    if cantidad:
                        cambio = True
                    if reactor.energia_actual == 0:
                        jugador.extrayendo = False
                        cambio = True
                    if self._verificar_fin(partida, ahora):
                        cambio = True
                        break

                if partida.estado == 'JUGANDO':
                    segundo_actual = math.ceil(partida.tiempo_restante(ahora))
                    if segundo_actual != partida.ultimo_segundo_notificado:
                        partida.ultimo_segundo_notificado = segundo_actual
                        cambio = True

                if cambio:
                    cambios.append((partida.id_partida, self._estado(partida, ahora)))
        return cambios
    
    def interrumpir_por_dano(self, id_partida, id_jugador):
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            if not partida:
                return False
            self._verificar_fin(partida)
            if partida.estado != 'JUGANDO':
                return False
            jugador = self._jugador(partida, id_jugador)
            if not jugador or not jugador.extrayendo:
                return False
            jugador.extrayendo = False
            return True