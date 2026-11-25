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


class ResultadoRecibido(Base):
    """Idempotencia del cierre recibido del servidor de partidas (US-023).

    Tabla nueva: no exige modificar las tablas de la base de datos existentes.
    """

    __tablename__ = "resultados_recibidos"

    id_externo: Mapped[str] = mapped_column(String(32), primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"), unique=True)
    huella: Mapped[str] = mapped_column(String(64))
    motivo_fin: Mapped[str] = mapped_column(String(20))
    fecha_recibido: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


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


class CodigoVerificacion(Base):
    """Código de 6 números para verificar el correo al registrarse (US-003).

    Se guarda cifrado, vence a las 24 horas y sirve una sola vez.
    """

    __tablename__ = "codigos_verificacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugadores.id"))
    codigo_hash: Mapped[str] = mapped_column(String(64))
    vence: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    intentos: Mapped[int] = mapped_column(Integer, default=0)  # intentos fallidos
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class CuentaSocial(Base):
    """Une a un jugador con su cuenta de Google o GitHub (US-002).

    Se guarda el id que da el proveedor (no el correo), porque el correo de una
    cuenta de Google o GitHub puede cambiar, pero ese id no.
    Un jugador puede tener varias: por ejemplo Google y GitHub a la vez.
    """

    __tablename__ = "cuentas_sociales"
    __table_args__ = (UniqueConstraint("proveedor", "proveedor_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jugador_id: Mapped[int] = mapped_column(ForeignKey("jugadores.id"))
    proveedor: Mapped[str] = mapped_column(String(20))  # google o github
    proveedor_id: Mapped[str] = mapped_column(String(100))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class InicioSocial(Base):
    """Un inicio de sesión con red social que está en proceso (US-002).

    El juego abre el navegador y se queda esperando. Cuando el jugador termina en
    Google o GitHub, el backend anota aquí quién era, y el juego lo recoge.
    - `state_hash`: viaja por el navegador; sirve para saber a qué inicio pertenece
      la respuesta de Google/GitHub y para evitar ataques CSRF.
    - `espera_hash`: solo lo conoce el juego; con él recoge el token al final.
    Los dos se guardan cifrados, vencen a los 10 minutos y sirven una sola vez.
    """

    __tablename__ = "inicios_sociales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proveedor: Mapped[str] = mapped_column(String(20))
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    espera_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    vence: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Se llena cuando el jugador termina en el navegador
    jugador_id: Mapped[int | None] = mapped_column(ForeignKey("jugadores.id"), nullable=True)
    error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)  # el juego ya recogió el token
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
