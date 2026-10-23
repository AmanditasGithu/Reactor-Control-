"""Lógica de las cuentas de jugador: registro (US-001)."""
from app.models import Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.schemas import RegistroRequest
from app.security import cifrar_contrasena


class CorreoYaRegistrado(Exception):
    """RN-01: el correo ya pertenece a otro jugador."""


class NombreUsuarioYaRegistrado(Exception):
    """RN-02: el nombre de usuario ya está en uso."""


class AuthService:
    """Reglas de negocio de las cuentas. No sabe nada de HTTP ni de SQL."""

    def __init__(self, repositorio: JugadorRepository):
        self.repositorio = repositorio

    def registrar(self, datos: RegistroRequest) -> Jugador:
        if self.repositorio.buscar_por_correo(datos.correo):
            raise CorreoYaRegistrado()
        if self.repositorio.buscar_por_nombre_usuario(datos.nombre_usuario):
            raise NombreUsuarioYaRegistrado()

        jugador = Jugador(
            nombre_usuario=datos.nombre_usuario,
            correo=datos.correo,
            contrasena_hash=cifrar_contrasena(datos.contrasena),
            proveedor="local",
            correo_verificado=False,  # se activa con la verificación de correo (US-003)
        )
        return self.repositorio.guardar(jugador)