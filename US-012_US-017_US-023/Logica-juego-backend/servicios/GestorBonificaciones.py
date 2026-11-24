"""Genera coleccionables y asigna el efecto solo al primer jugador en la casilla.

Los métodos son síncronos y se invocan dentro de GestordePartida.bloqueo.
Ningún cliente puede elegir puntos, duración ni el ganador de una bonificación.
"""
from modelos.Bonificacion import Bonificacion, EfectoBonificacion


class GestorBonificaciones:
    POSICIONES = ((4, 4), (6, 4), (4, 6), (6, 6))

    def actualizar(self, partida, ahora):
        if partida.estado != 'JUGANDO':
            return False
        cambio = False
        for jugador in partida.jugadores:
            efecto = jugador.bonificacion_activa
            if efecto is not None and not efecto.activo(ahora):
                jugador.bonificacion_activa = None
                cambio = True

        disponible = partida.bonificacion_disponible
        if disponible is not None and ahora >= disponible.caduca_en:
            partida.bonificacion_disponible = None
            cambio = True

        if (partida.bonificacion_disponible is None
                and partida.proxima_bonificacion is not None
                and ahora >= partida.proxima_bonificacion):
            posiciones_ocupadas = {(j.x, j.y) for j in partida.jugadores}
            libres = [p for p in self.POSICIONES if p not in posiciones_ocupadas]
            if libres:
                posicion = libres[partida.indice_posicion_bonificacion % len(libres)]
                partida.indice_posicion_bonificacion += 1
                partida.bonificacion_disponible = Bonificacion(
                    id_bonificacion=partida.siguiente_id_bonificacion,
                    x=posicion[0], y=posicion[1],
                    caduca_en=ahora + partida.tiempo_en_mapa_bonificacion,
                    duracion_efecto=partida.duracion_efecto_bonificacion,
                )
                partida.siguiente_id_bonificacion += 1
                partida.proxima_bonificacion = ahora + partida.intervalo_bonificaciones
                cambio = True
            else:
                # Evita generación sobre un jugador; reintenta próximamente.
                partida.proxima_bonificacion = ahora + 1.0
        return cambio

    def intentar_recoger(self, partida, jugador, ahora):
        if partida.estado != 'JUGANDO':
            return None
        disponible = partida.bonificacion_disponible
        if disponible is None or ahora >= disponible.caduca_en:
            return None
        if not disponible.jugador_encima(jugador):
            return None

        jugador.bonificacion_activa = EfectoBonificacion(
            id_bonificacion=disponible.id_bonificacion,
            tipo=disponible.tipo,
            multiplicador=disponible.multiplicador,
            expira_en=ahora + disponible.duracion_efecto,
        )
        partida.bonificacion_disponible = None
        return {
            'id_bonificacion': disponible.id_bonificacion,
            'id_jugador': jugador.id_jugador,
            'tipo_bonificacion': disponible.tipo,
            'multiplicador': disponible.multiplicador,
            'duracion_segundos': disponible.duracion_efecto,
        }
