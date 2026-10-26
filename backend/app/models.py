"""Modelos de la base de datos: cada clase es una tabla.

Basado en el diagrama de despliegue; usuarios, credenciales,
partidas, puntajes, eventos, ranking y estadísticas.
El ranking no tiene tabla propia: se calcula a partir de `participaciones`.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Jugador(Base):
    """Usuarios, credenciales y estadísticas acumuladas."""

    __tablename__ = "jugadores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column(String(30), unique=True, index=True)  # RN-02
    correo: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # RN-01
    # Contraseña cifrada (RNF-04). Vacía si la cuenta se creó con una red social.
    contrasena_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proveedor: Mapped[str] = mapped_column(String(20), default="local")  # local, google, github...
    correo_verificado: Mapped[bool] = mapped_column(Boolean, default=False)  # US-003
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    # Estadísticas acumuladas (US-006)
    puntos_totales: Mapped[int] = mapped_column(Integer, default=0)
    victorias: Mapped[int] = mapped_column(Integer, default=0)
    partidas_jugadas: Mapped[int] = mapped_column(Integer, default=0)

    participaciones: Mapped[list["Participacion"]] = relationship(back_populates="jugador")
    records: Mapped[list["Record"]] = relationship(back_populates="jugador")


class Partida(Base):
    """Una partida jugada en la arena."""

    __tablename__ = "partidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    escenario: Mapped[str] = mapped_column(String(50), default="laboratorio")
    # en_espera, en_curso o finalizada
    estado: Mapped[str] = mapped_column(String(20), default="en_espera")
    puntuacion_objetivo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duracion_segundos: Mapped[int] = mapped_column(Integer, default=300)
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ganador_id: Mapped[int | None] = mapped_column(ForeignKey("jugadores.id"), nullable=True)

    participaciones: Mapped[list["Participacion"]] = relationship(back_populates="partida")
    eventos: Mapped[list["EventoPartida"]] = relationship(back_populates="partida")


class Participacion(Base):
    """Puntaje de un jugador en una partida (tabla intermedia)."""

    __tablename__ = "participaciones"
    __table_args__ = (UniqueConstraint("partida_id", "jugador_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"))
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugadores.id"))
    puntos: Mapped[int] = mapped_column(Integer, default=0)
    posicion: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1, 2, 3... (podio)

    partida: Mapped[Partida] = relationship(back_populates="participaciones")
    jugador: Mapped[Jugador] = relationship(back_populates="participaciones")


class EventoPartida(Base):
    """Algo que pasó durante una partida: extracción, terminal, penalización..."""

    __tablename__ = "eventos_partida"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"))
    jugador_id: Mapped[int | None] = mapped_column(ForeignKey("jugadores.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(40))  # extraccion_reactor, terminal, penalizacion...
    puntos: Mapped[int] = mapped_column(Integer, default=0)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    partida: Mapped[Partida] = relationship(back_populates="eventos")


class Record(Base):
    """Récords históricos de cada jugador."""

    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugadores.id"))
    partida_id: Mapped[int | None] = mapped_column(ForeignKey("partidas.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(40))  # mayor_puntuacion, mas_energia...
    valor: Mapped[int] = mapped_column(Integer)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    jugador: Mapped[Jugador] = relationship(back_populates="records")


class CodigoRecuperacion(Base):
    """Código de 6 números para recuperar la contraseña (US-005).

    Se guarda cifrado, vence a los 15 minutos y sirve una sola vez.
    """

    __tablename__ = "codigos_recuperacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugadores.id"))
    codigo_hash: Mapped[str] = mapped_column(String(64))
    vence: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)  # intentos fallidos
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
