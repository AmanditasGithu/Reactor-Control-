"""Modelos de un objeto coleccionable y su efecto temporal (US-012)."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Bonificacion:
    id_bonificacion: int
    x: int
    y: int
    caduca_en: float
    duracion_efecto: float
    tipo: str = 'DOBLE_PUNTOS'
    multiplicador: int = 2

    def jugador_encima(self, jugador):
        return jugador.x == self.x and jugador.y == self.y

    def obtener_estado(self, ahora):
        return {
            'id_bonificacion': self.id_bonificacion,
            'tipo': self.tipo,
            'x': self.x,
            'y': self.y,
            'multiplicador': self.multiplicador,
            'segundos_restantes': max(0, math.ceil(self.caduca_en - ahora)),
        }


@dataclass(frozen=True)
class EfectoBonificacion:
    id_bonificacion: int
    expira_en: float
    tipo: str = 'DOBLE_PUNTOS'
    multiplicador: int = 2

    def activo(self, ahora):
        return ahora < self.expira_en

    def obtener_estado(self, ahora):
        return {
            'id_bonificacion': self.id_bonificacion,
            'tipo': self.tipo,
            'multiplicador': self.multiplicador,
            'segundos_restantes': max(0, math.ceil(self.expira_en - ahora)),
        }
