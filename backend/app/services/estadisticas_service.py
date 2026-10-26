"""Perfil del jugador (US-006), ranking global (US-022) y registro de resultados."""
from dataclasses import dataclass

from app.models import Jugador, Participacion, Partida, Record
from app.repositories.estadisticas_repository import EstadisticasRepository
from app.schemas import FilaRanking, PartidaEnHistorial, PerfilResponse, RecordResponse

PARTIDAS_EN_HISTORIAL = 10


@dataclass
class ResultadoJugador:
    """Cómo le fue a un jugador en una partida. Lo usa quien cierra la partida (US-019/US-020)."""

    jugador_id: int
    puntos: int
    posicion: int


class EstadisticasService:
    def __init__(self, repositorio: EstadisticasRepository):
        self.repositorio = repositorio

    def ranking(self, limite: int = 10) -> list[FilaRanking]:
        """US-022: top de jugadores por puntos acumulados."""
        filas = []
        for jugador in self.repositorio.ranking(limite):
            filas.append(
                FilaRanking(
                    posicion=self.repositorio.posicion(jugador),
                    nombre_usuario=jugador.nombre_usuario,
                    puntos_totales=jugador.puntos_totales,
                    victorias=jugador.victorias,
                    partidas_jugadas=jugador.partidas_jugadas,
                )
            )
        return filas

    def perfil(self, jugador: Jugador) -> PerfilResponse:
        """US-006: datos, estadísticas, historial y récords del jugador."""
        historial = [
            PartidaEnHistorial(
                partida_id=partida.id,
                escenario=partida.escenario,
                fecha=partida.fecha_fin or partida.fecha_inicio,
                puntos=participacion.puntos,
                posicion=participacion.posicion,
            )
            for participacion, partida in self.repositorio.historial(jugador.id, PARTIDAS_EN_HISTORIAL)
        ]
        return PerfilResponse(
            nombre_usuario=jugador.nombre_usuario,
            correo=jugador.correo,
            fecha_registro=jugador.fecha_registro,
            puntos_totales=jugador.puntos_totales,
            victorias=jugador.victorias,
            partidas_jugadas=jugador.partidas_jugadas,
            posicion_ranking=self.repositorio.posicion(jugador),
            historial=historial,
            records=[RecordResponse.model_validate(r) for r in self.repositorio.records(jugador.id)],
        )

    def registrar_resultado(self, partida: Partida, resultados: list[ResultadoJugador]) -> None:
        """Guarda los puntos de una partida terminada y actualiza estadísticas y récords.

        Se llama una vez, cuando la partida termina (US-019). Así el perfil y el ranking
        quedan al día solos.
        """
        cambios = []
        for resultado in resultados:
            jugador = self.repositorio.buscar_jugador(resultado.jugador_id)
            if jugador is None:
                continue

            participacion = self.repositorio.buscar_participacion(
                partida.id, jugador.id
            ) or Participacion(partida_id=partida.id, jugador_id=jugador.id)
            participacion.puntos = resultado.puntos
            participacion.posicion = resultado.posicion
            cambios.append(participacion)

            jugador.puntos_totales += resultado.puntos
            jugador.partidas_jugadas += 1
            if resultado.posicion == 1:
                jugador.victorias += 1
                partida.ganador_id = jugador.id

            record = self.repositorio.buscar_record(jugador.id, "mayor_puntuacion")
            if record is None:
                cambios.append(Record(jugador_id=jugador.id, partida_id=partida.id,
                                      tipo="mayor_puntuacion", valor=resultado.puntos))
            elif resultado.puntos > record.valor:
                record.valor = resultado.puntos
                record.partida_id = partida.id

        cambios.append(partida)
        self.repositorio.guardar_todo(cambios)
