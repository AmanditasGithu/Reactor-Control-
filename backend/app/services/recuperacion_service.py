"""Lógica para recuperar la contraseña (US-005).

Paso 1: el jugador pide un código con su correo. El código se "envía" por correo.
Paso 2: el jugador escribe el código y su contraseña nueva.
"""
from datetime import datetime, timedelta, timezone

from app.correo import enviar_correo
from app.models import CodigoRecuperacion
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.recuperacion_repository import RecuperacionRepository
from app.schemas import RestablecerContrasenaRequest
from app.security import cifrar_codigo, cifrar_contrasena, generar_codigo

MINUTOS_VALIDEZ = 15
MAXIMO_INTENTOS = 5


class CodigoInvalido(Exception):
    """El código no existe, está mal, ya se usó, venció o se agotaron los intentos."""


class RecuperacionService:
    def __init__(self, jugadores: JugadorRepository, codigos: RecuperacionRepository):
        self.jugadores = jugadores
        self.codigos = codigos

    def solicitar_codigo(self, correo: str) -> None:
        """Crea un código y lo envía. Si el correo no existe no hace nada,
        pero la ruta responde igual: así nadie averigua qué correos están registrados."""
        jugador = self.jugadores.buscar_por_correo(correo)
        if jugador is None or jugador.contrasena_hash is None:  # sin cuenta, o cuenta de red social
            return

        codigo = generar_codigo()
        self.codigos.anular_codigos(jugador.id)
        self.codigos.agregar(
            CodigoRecuperacion(
                jugador_id=jugador.id,
                codigo_hash=cifrar_codigo(codigo),
                vence=datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_VALIDEZ),
            )
        )
        self.codigos.guardar_cambios()

        enviar_correo(
            jugador.correo,
            "Recuperar contraseña - Control del Reactor",
            f"Hola {jugador.nombre_usuario}, tu código es: {codigo}\n"
            f"Vence en {MINUTOS_VALIDEZ} minutos. Si no lo pediste, ignorá este correo.",
        )

    def restablecer(self, datos: RestablecerContrasenaRequest) -> None:
        """Cambia la contraseña si el código es correcto."""
        jugador = self.jugadores.buscar_por_correo(datos.correo)
        registro = self.codigos.codigo_vigente(jugador.id) if jugador else None
        if registro is None:
            raise CodigoInvalido()

        vence = registro.vence
        if vence.tzinfo is None:  # SQLite guarda las fechas sin zona horaria
            vence = vence.replace(tzinfo=timezone.utc)
        if vence < datetime.now(timezone.utc) or registro.intentos >= MAXIMO_INTENTOS:
            raise CodigoInvalido()

        if registro.codigo_hash != cifrar_codigo(datos.codigo):
            registro.intentos += 1
            self.codigos.guardar_cambios()
            raise CodigoInvalido()

        registro.usado = True  # el código sirve una sola vez
        jugador.contrasena_hash = cifrar_contrasena(datos.contrasena_nueva)
        self.codigos.guardar_cambios()
