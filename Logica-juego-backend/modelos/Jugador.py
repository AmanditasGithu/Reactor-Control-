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

    def mover(self, direccion):
        if direccion == "ARRIBA":
            self.y -= self.velocidad
        elif direccion == "ABAJO":
            self.y += self.velocidad
        elif direccion == "DERECHA":
            self.x += self.velocidad
        elif direccion == "IZQUIERDA":
            self.x -= self.velocidad
    
    def sumar_puntos(self, cantidad):
        self.puntos += cantidad