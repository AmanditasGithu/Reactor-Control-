"""Lógica para verificar el correo del jugador (US-003).

Al registrarse, el jugador recibe un código de 6 números por correo.
Al escribirlo, su cuenta queda con el correo verificado.
"""
from datetime import datetime, timedelta, timezone

from app.correo import enviar_correo
from app.models import CodigoVerificacion, Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.verificacion_repository import VerificacionRepository
from app.schemas import VerificarCorreoRequest
from app.security import cifrar_codigo, generar_codigo

HORAS_VALIDEZ = 24
MAXIMO_INTENTOS = 5


class CodigoVerificacionInvalido(Exception):
    """El código no existe, está mal, ya se usó, venció o se agotaron los intentos."""


class VerificacionService:
    def __init__(self, jugadores: JugadorRepository, codigos: VerificacionRepository):
        self.jugadores = jugadores
        self.codigos = codigos

    def enviar_codigo(self, jugador: Jugador) -> None:
        """Crea un código nuevo (anulando los anteriores) y lo envía al correo del jugador."""
        codigo = generar_codigo()
        self.codigos.anular_codigos(jugador.id)
        self.codigos.agregar(
            CodigoVerificacion(
                jugador_id=jugador.id,
                codigo_hash=cifrar_codigo(codigo),
                vence=datetime.now(timezone.utc) + timedelta(hours=HORAS_VALIDEZ),
            )
        )
        self.codigos.guardar_cambios()

        enviar_correo(
            jugador.correo,
            "Verificá tu correo - Control del Reactor",
            f"Hola {jugador.nombre_usuario}, tu código de verificación es: {codigo}\n"
            f"Vence en {HORAS_VALIDEZ} horas.",
        )

    def reenviar(self, correo: str) -> None:
        """Manda otro código. Si el correo no existe o ya está verificado, no hace nada
        (la ruta responde igual, para no revelar qué correos están registrados)."""
        jugador = self.jugadores.buscar_por_correo(correo)
        if jugador is None or jugador.correo_verificado:
            return
        self.enviar_codigo(jugador)

    def verificar(self, datos: VerificarCorreoRequest) -> None:
        """Marca el correo como verificado si el código es correcto."""
        jugador = self.jugadores.buscar_por_correo(datos.correo)
        if jugador is not None and jugador.correo_verificado:
            return  # ya estaba verificado: no hay nada que hacer

        registro = self.codigos.codigo_vigente(jugador.id) if jugador else None
        if registro is None:
            raise CodigoVerificacionInvalido()

        vence = registro.vence
        if vence.tzinfo is None:  # SQLite guarda las fechas sin zona horaria
            vence = vence.replace(tzinfo=timezone.utc)
        if vence < datetime.now(timezone.utc) or registro.intentos >= MAXIMO_INTENTOS:
            raise CodigoVerificacionInvalido()

        if registro.codigo_hash != cifrar_codigo(datos.codigo):
            registro.intentos += 1
            self.codigos.guardar_cambios()
            raise CodigoVerificacionInvalido()

        registro.usado = True
        jugador.correo_verificado = True
        self.codigos.guardar_cambios()
