import time


class Jugador:

    def __init__(self, id_jugador, nombre):
        self.id_jugador = id_jugador
        self.nombre = nombre
        self.extrayendo = False
        self.ultimo_latido_accion = 0.0
        self.ultimo_ciclo_extraccion = 0.0

        self.x = 0
        self.y = 0

        self.puntos = 0
        self.velocidad = 1
        self.bonificacion_activa = None

    def mover(self, direccion):
        if direccion == "ARRIBA":
            self.y -= self.velocidad
        elif direccion == "ABAJO":
            self.y += self.velocidad
        elif direccion == "DERECHA":
            self.x += self.velocidad
        elif direccion == "IZQUIERDA":
            self.x -= self.velocidad
    
    def sumar_puntos(self, cantidad, ahora=None):
        """Aplica el multiplicador únicamente a recompensas positivas y vigentes."""
        if ahora is None:
            ahora = time.monotonic()
        efecto = self.bonificacion_activa
        multiplicador = (
            efecto.multiplicador if cantidad > 0 and efecto is not None
            and efecto.activo(ahora) else 1
        )
        ganados = int(cantidad * multiplicador)
        self.puntos += ganados
        return ganados