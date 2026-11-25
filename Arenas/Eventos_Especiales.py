#Evento pulso reactor para la Planta Industrial
#Este evento es exclusivo para la planta industrial.
#Este evento ocurre solo una vez en la partida
#Si el primer digito de la puntuacion del jugador es par -30pts
#Si es impar suma +20 pts.

#Evento transferencia de celdas para el Laboratorio subterraneo
#Este evento es exclusivo para el laboratorio subterraneo
#Este evento ocurre solo una vez en la partida
#Transfiere el puntaje de todas las celdas de un jugador a otro


#Evento de reduccion de energia para el complejo militar 
#Este evento es exclusivo para el laboratorio subterraneo
#Este evento ocurre solo una vez en la partida
#La energia recaudada por los jugadores se reduce a la mitad

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
    
class EventoTransferenciaCeldasLab:
    def __init__(self, duracion_anuncio=4.5):
        self.duracion_anuncio = duracion_anuncio
        self.ya_ocurrio = False
        self.tiempo_fin_anuncio = 0.0
        self.mensaje_actual = None
        self.color_borde = (0, 225, 255)
        self.celdas_transferidas = 0
        self.nombre_receptor = "RIVAL"

    def _buscar_otro_jugador(self, partida, jugador_logico):
        if partida and getattr(partida, "jugadores", None):
            for j in partida.jugadores:
                if getattr(j, "id_jugador", None) != getattr(jugador_logico, "id_jugador", None):
                    return j
        return None

    def actualizar(self, partida, jugador_logico, ahora, celdas_jugador=0, rivales=None):
        self.celdas_transferidas = 0

        if not self.ya_ocurrio and partida.estado == "JUGANDO":
            mitad_partida = partida.duracion * 0.5
            if partida.tiempo_restante(ahora) <= mitad_partida:
                self.ya_ocurrio = True
                cantidad = max(0, int(celdas_jugador))
                receptor = self._buscar_otro_jugador(partida, jugador_logico)

                if receptor is not None:
                    self.nombre_receptor = str(getattr(receptor, "nombre", "RIVAL")).upper()
                elif rivales:
                    self.nombre_receptor = str(rivales[0].get("nombre", "RIVAL")).upper()

                if cantidad > 0:
                    self.celdas_transferidas = cantidad
                    if receptor is not None:
                        actual_celdas = getattr(receptor, "celdas", 0)
                        setattr(receptor, "celdas", actual_celdas + cantidad)
                    self.mensaje_actual = f"FALLO DE CONTENCION! {cantidad} CELDA(S) -> {self.nombre_receptor}"
                    self.color_borde = (255, 80, 120)
                else:
                    self.mensaje_actual = f"PULSO SUBTERRANEO! 0 CELDAS PARA {self.nombre_receptor}"
                    self.color_borde = (0, 225, 255)

                self.tiempo_fin_anuncio = ahora + self.duracion_anuncio

        if self.mensaje_actual and ahora > self.tiempo_fin_anuncio:
            self.mensaje_actual = None


    def obtener_anuncio(self, ahora):
        if self.mensaje_actual and ahora <= self.tiempo_fin_anuncio:
            return self.mensaje_actual, self.color_borde
        return None, None

class EventoReduccionEnergiaMilitar:
    def __init__(self):
        self.activado = False
        self.tiempo_anuncio = 0.0
        self.duracion_anuncio = 3.5
        self.texto_anuncio = ""
        self.color_anuncio = (255, 70, 70)

    def actualizar(self, partida, jugador_logico, ahora):
        if self.activado:
            return

        duracion_total = getattr(partida, "duracion", None) or getattr(partida, "tiempo_total", None)
        restante = partida.tiempo_restante(ahora)

        if duracion_total and duracion_total > 0:
            mitad_alcanzada = restante <= (duracion_total * 0.5)
        else:
            if not hasattr(self, "_tiempo_inicial"):
                self._tiempo_inicial = max(restante, 1.0)
            mitad_alcanzada = restante <= (self._tiempo_inicial * 0.5)

        if mitad_alcanzada:
            self.activado = True
            self.tiempo_anuncio = ahora
            self.texto_anuncio = "¡CORTE TÁCTICO: -50% ENERGÍA!"
            self.color_anuncio = (255, 65, 65)

            # Reduce a la mitad la energia
            for j in getattr(partida, "jugadores", []):
                if hasattr(j, "energia"):
                    j.energia = max(0, j.energia // 2)
                if hasattr(j, "energia_extraida"):
                    j.energia_extraida = max(0, j.energia_extraida // 2)

            if hasattr(jugador_logico, "energia"):
                jugador_logico.energia = max(0, jugador_logico.energia // 2)

    def obtener_anuncio(self, ahora):
        if self.texto_anuncio and (ahora - self.tiempo_anuncio) <= self.duracion_anuncio:
            return self.texto_anuncio, self.color_anuncio
        return None, None


class FabricaEventosEscenario:
    @staticmethod
    def crear_evento(escenario):
        clave = (escenario or "").strip().lower()
        if clave in ("planta_industrial", "industrial", "reactor"):
            return EventoPulsoReactor()
        if clave in ("laboratorio_subterraneo", "laboratorio", "subterraneo", "lab"):
            return EventoTransferenciaCeldasLab()
        if clave in ("complejo_militar", "militar", "complejo"):
            return EventoReduccionEnergiaMilitar()
        return None



