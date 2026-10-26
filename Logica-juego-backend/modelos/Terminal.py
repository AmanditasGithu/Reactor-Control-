class Terminal:

    def __init__(self, id_terminal, x, y, puntos=10):

        self.id_terminal = id_terminal

        self.x = x
        self.y = y

        self.puntos = puntos

        self.activada = False
        self.activada_por = None

    def jugador_encima(self, jugador):

        return (
            jugador.x == self.x
            and jugador.y == self.y
        )

    def activar(self, jugador):

        if self.activada:
            return False

        if not self.jugador_encima(jugador):
            return False

        self.activada = True
        self.activada_por = jugador.id_jugador

        jugador.sumar_puntos(self.puntos)

        return True

    def obtener_estado(self):

        return {
            "id_terminal": self.id_terminal,
            "x": self.x,
            "y": self.y,
            "puntos": self.puntos,
            "activada": self.activada,
            "activada_por": self.activada_por
        }
