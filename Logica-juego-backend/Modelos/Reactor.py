from math import dist

class Reactor:

    def __init__(
        self,
        x=5,
        y=5,
        radio=2,
        energia_maxima=100,
        energia_por_ciclo=5,
        puntos_por_energia=1,
        intervalo=0.5,
        espera_recarga=10
    ):

        self.x = x
        self.y = y
        self.radio = radio

        self.energia_maxima = energia_maxima
        self.energia_actual = energia_maxima

        self.energia_por_ciclo = energia_por_ciclo
        self.puntos_por_energia = puntos_por_energia

        self.intervalo = intervalo
        self.espera_recarga = espera_recarga
        self.proxima_recarga = None

    def jugador_cerca(self, jugador):
        distancia = dist(
            (jugador.x, jugador.y),
            (self.x, self.y)
        )
        return distancia <= self.radio

    def extraer(self, jugador, ahora):

        if not self.jugador_cerca(jugador):
            return 0

        if self.energia_actual <= 0:
            return 0

        cantidad = min(
            self.energia_por_ciclo,
            self.energia_actual
        )

        self.energia_actual -= cantidad

        puntos = cantidad * self.puntos_por_energia

        jugador.sumar_puntos(puntos)

        if self.energia_actual == 0:
            self.proxima_recarga = (
                ahora + self.espera_recarga
            )

        return cantidad

    def recargar_si_corresponde(self, ahora):

        if self.proxima_recarga is None:
            return False

        if ahora < self.proxima_recarga:
            return False

        self.energia_actual = self.energia_maxima
        self.proxima_recarga = None

        return True

    def obtener_estado(self):

        return {
            "x": self.x,
            "y": self.y,
            "radio": self.radio,
            "energia_actual": self.energia_actual,
            "energia_maxima": self.energia_maxima,
            "recargando": self.proxima_recarga is not None
        }
