import time 
import math

from threading import RLock
from modelos.Partida import Partida
from modelos.Terminal import Terminal
from servicios.GestorBonificaciones import GestorBonificaciones

class GestordePartida:
    TIEMPO_MAX_SIN_LATIDO = 1.5

    def __init__(self):
        self.partidas = {}
        self.siguiente_id = 1
        self.bloqueo = RLock()
        self._eventos_finalizacion = []
        self.bonificaciones = GestorBonificaciones()
    
    def crear_partida(self, escenario=None):
        with self.bloqueo:
            partida = Partida(self.siguiente_id)
            partida.escenario = escenario
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
                 'escenario': p.escenario,
                 'cantidad_jugadores': len(p.jugadores)}
                for p in self.partidas.values()
            ]

    def _verificar_fin(self, partida, ahora=None):
        if partida.finalizar_si_corresponde(ahora):
            partida.bonificacion_disponible = None
            for jugador in partida.jugadores:
                jugador.bonificacion_activa = None
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
        if ahora is None:
            ahora = time.monotonic()
        disponible = partida.bonificacion_disponible
        return {
            'id_partida': partida.id_partida,
            'id_externo': partida.id_externo,
            'fecha_inicio_utc': partida.fecha_inicio_utc,
            'fecha_fin_utc': partida.fecha_fin_utc,
            'estado': partida.estado,
            'escenario': partida.escenario,
            'celdas': sorted(list(c) for c in partida.celdas) if partida.celdas is not None else None,
            'duracion': partida.duracion,
            'puntuacion_objetivo': partida.meta,
            'tiempo_restante': round(partida.tiempo_restante(ahora), 2),
            'motivo_fin': partida.motivo_fin,
            'resultados_finales': partida.resultados_finales,
            'jugadores': [
                {'id_jugador': j.id_jugador, 'nombre': j.nombre,
                 'x': j.x, 'y': j.y, 'puntos': j.puntos,
                 'extrayendo': j.extrayendo,
                 'bonificacion': (j.bonificacion_activa.obtener_estado(ahora)
                                  if j.bonificacion_activa and j.bonificacion_activa.activo(ahora)
                                  else None)}
                for j in partida.jugadores
            ],
            'bonificacion_disponible': (
                disponible.obtener_estado(ahora)
                if disponible is not None and ahora < disponible.caduca_en
                else None
            ),
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
            
            ahora = time.monotonic()
            self.bonificaciones.actualizar(partida, ahora)
            jugador.mover(direccion)
            bonificacion_recogida = self.bonificaciones.intentar_recoger(
                partida, jugador, ahora
            )

            terminal_activada = None
            
            for terminal in partida.terminales:
                puntos_antes = jugador.puntos
                if terminal.activar(jugador, ahora=ahora):
                    terminal_activada = {
                        'id_terminal': terminal.id_terminal,
                        'id_jugador': jugador.id_jugador,
                        'puntos_obtenidos': jugador.puntos - puntos_antes
                    }
                    
                    break

            self._verificar_fin(partida)
            return {
                'ok': True,
                'terminal_activada': terminal_activada,
                'bonificacion_recogida': bonificacion_recogida,
                'estado': self._estado(partida, ahora),
            }
    
    def configurar_mapa(self, id_partida, reactor, terminales, bonificaciones, celdas=None):
        """Multijugador: usa las posiciones del mapa de la arena. Solo la primera vez."""
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            if not partida or partida.mapa_configurado or partida.estado == 'FINALIZADA':
                return False
            partida.reactor.x, partida.reactor.y = int(reactor[0]), int(reactor[1])
            if terminales:
                partida.terminales = [
                    Terminal(id_terminal=i, x=int(x), y=int(y), puntos=10)
                    for i, (x, y) in enumerate(terminales[:10], 1)
                ]
            if bonificaciones:
                partida.posiciones_bonificacion = [(int(x), int(y)) for x, y in bonificaciones[:60]]
            if celdas:
                partida.celdas = {(int(x), int(y)) for x, y in celdas[:60]}
            partida.mapa_configurado = True
            return True

    def recoger_celda(self, id_partida, id_jugador, x, y):
        """Celda de energía del mapa: +10 para quien la toca primero (tiene que estar al lado)."""
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            if not partida or partida.estado != 'JUGANDO' or not partida.celdas:
                return None
            jugador = self._jugador(partida, id_jugador)
            celda = (int(x), int(y))
            if not jugador or celda not in partida.celdas:
                return None
            if abs(jugador.x - celda[0]) > 1 or abs(jugador.y - celda[1]) > 1:
                return None
            ahora = time.monotonic()
            partida.celdas.discard(celda)
            jugador.sumar_puntos(10, ahora)
            self._verificar_fin(partida)
            return self._estado(partida, ahora)

    def ubicar_jugador(self, id_partida, id_jugador, x, y):
        """Multijugador: la arena de la compu informa en qué casilla está su jugador.

        La arena maneja las paredes; el servidor acepta pasos cortos (máximo 3 casillas)
        para que nadie se teletransporte. La primera vez sí puede ubicarse donde empieza.
        """
        with self.bloqueo:
            partida = self.partidas.get(id_partida)
            if not partida or partida.estado != 'JUGANDO':
                return {'ok': False}
            self._verificar_fin(partida)
            jugador = self._jugador(partida, id_jugador)
            if partida.estado != 'JUGANDO' or not jugador or jugador.extrayendo:
                return {'ok': False}
            x, y = int(x), int(y)
            if getattr(jugador, 'ubicado', False) and abs(x - jugador.x) + abs(y - jugador.y) > 3:
                return {'ok': False}
            jugador.ubicado = True
            if (x, y) == (jugador.x, jugador.y):
                return {'ok': True, 'cambio': False}
            ahora = time.monotonic()
            self.bonificaciones.actualizar(partida, ahora)
            jugador.x, jugador.y = x, y
            bonificacion_recogida = self.bonificaciones.intentar_recoger(partida, jugador, ahora)
            terminal_activada = None
            for terminal in partida.terminales:
                puntos_antes = jugador.puntos
                if terminal.activar(jugador, ahora=ahora):
                    terminal_activada = {
                        'id_terminal': terminal.id_terminal,
                        'id_jugador': jugador.id_jugador,
                        'puntos_obtenidos': jugador.puntos - puntos_antes,
                    }
                    break
            self._verificar_fin(partida)
            return {'ok': True, 'cambio': True, 'terminal_activada': terminal_activada,
                    'bonificacion_recogida': bonificacion_recogida,
                    'estado': self._estado(partida, ahora)}

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
                cambio = self.bonificaciones.actualizar(partida, ahora)
                cambio = reactor.recargar_si_corresponde(ahora) or cambio
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