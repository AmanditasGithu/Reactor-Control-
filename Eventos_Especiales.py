#Evento pulso reactor para la Planta Industrial
#Este evento es exclusivo para la planta industrial.
#Este evento ocurre solo una vez en la partida
#Si el primer digito de la puntuacion del jugador es par -30pts
#Si es impar suma +20 pts.
class EventoPulsoReactor:
    def __init__(self, duracion_anuncio=4.5):
        self.duracion_anuncio = duracion_anuncio
        self.ya_ocurrio = False
        self.tiempo_fin_anuncio = 0.0
        self.mensaje_actual = None
        self.color_borde = (255, 200, 0)

    def actualizar(self, partida, jugador_logico, ahora):
        if not self.ya_ocurrio and partida.estado == "JUGANDO":
            mitad_partida = partida.duracion * 0.5
            if partida.tiempo_restante(ahora) <= mitad_partida:
                self.ya_ocurrio = True
                pts_actuales = max(0, int(jugador_logico.puntos))
                primer_digito = int(str(pts_actuales)[0])

                if primer_digito % 2 == 0:
                    jugador_logico.puntos = max(0, jugador_logico.puntos - 30)
                    self.mensaje_actual = f"PULSO PAR ({primer_digito})! -30 PTS"
                    self.color_borde = (255, 65, 65)
                else:
                    jugador_logico.sumar_puntos(20)
                    self.mensaje_actual = f"PULSO IMPAR ({primer_digito})! +20 PTS"
                    self.color_borde = (50, 255, 140)

                self.tiempo_fin_anuncio = ahora + self.duracion_anuncio

        if self.mensaje_actual and ahora > self.tiempo_fin_anuncio:
            self.mensaje_actual = None

    def obtener_anuncio(self, ahora):
        if self.mensaje_actual and ahora <= self.tiempo_fin_anuncio:
            return self.mensaje_actual, self.color_borde
        return None, None


class FabricaEventosEscenario:
    @staticmethod
    def crear_evento(escenario):
        clave = (escenario or "").strip().lower()
        if clave in ("planta_industrial", "industrial", "reactor"):
            return EventoPulsoReactor()
        return None



