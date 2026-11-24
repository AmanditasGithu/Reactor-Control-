"""US-017: publicación de marcador autoritativo y energía del reactor.

Este servicio SOLO observa el estado que el servidor ya calculó.
No acepta puntuaciones enviadas por un cliente ni modifica Jugador.puntos.
"""
from threading import RLock


class MarcadorTiempoReal:
    def __init__(self):
        self.bloqueo = RLock()
        self._claves = {}
        self._revisiones = {}

    @staticmethod
    def _resumen(estado):
        jugadores = [
            {
                'id_jugador': j['id_jugador'],
                'nombre': j['nombre'],
                'puntos': j['puntos'],
                'extrayendo': j.get('extrayendo', False),
                'bonificacion': j.get('bonificacion'),
            }
            for j in sorted(
                estado['jugadores'],
                key=lambda j: (-j['puntos'], j['id_jugador'])
            )
        ]
        reactor = estado.get('reactor') or {}
        energia = {
            'energia_actual': reactor.get('energia_actual', 0),
            'energia_maxima': reactor.get('energia_maxima', 0),
            'recargando': reactor.get('recargando', False),
        }
        return {
            'tipo': 'marcador_actualizado',
            'id_partida': estado['id_partida'],
            'estado': estado['estado'],
            'puntuacion_objetivo': estado['puntuacion_objetivo'],
            'jugadores': jugadores,
            'bonificacion_disponible': estado.get('bonificacion_disponible'),
            'reactor': energia,
            'motivo_fin': estado.get('motivo_fin'),
        }

    @staticmethod
    def _clave(resumen):
        return (
            resumen['estado'],
            resumen['puntuacion_objetivo'],
            tuple((j['id_jugador'], j['nombre'], j['puntos'], j['extrayendo'],
                   repr(j['bonificacion'])) for j in resumen['jugadores']),
            repr(resumen['bonificacion_disponible']),
            tuple(sorted(resumen['reactor'].items())),
            resumen['motivo_fin'],
        )

    def evento_actual(self, estado):
        """Mensaje completo para el cliente que acaba de conectarse."""
        resumen = self._resumen(estado)
        id_partida = resumen['id_partida']
        clave = self._clave(resumen)
        with self.bloqueo:
            if self._claves.get(id_partida) != clave:
                self._revisiones[id_partida] = self._revisiones.get(id_partida, 0) + 1
                self._claves[id_partida] = clave
            resumen['revision'] = self._revisiones[id_partida]
        return resumen

    def evento_si_cambia(self, estado):
        """Evita publicaciones idénticas (p. ej. ticks del reloj)."""
        resumen = self._resumen(estado)
        id_partida = resumen['id_partida']
        clave = self._clave(resumen)
        with self.bloqueo:
            if self._claves.get(id_partida) == clave:
                return None
            self._revisiones[id_partida] = self._revisiones.get(id_partida, 0) + 1
            self._claves[id_partida] = clave
            resumen['revision'] = self._revisiones[id_partida]
        return resumen

    async def publicar_si_cambia(self, estado, conexiones):
        if estado is None:
            return False
        mensaje = self.evento_si_cambia(estado)
        if mensaje is None:
            return False
        await conexiones.enviar_a_partida(estado['id_partida'], mensaje)
        return True
