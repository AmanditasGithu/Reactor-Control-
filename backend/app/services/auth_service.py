"""Lógica de las cuentas de jugador: registro (US-001) e inicio de sesión (US-004)."""
from app.models import Jugador
from app.repositories.jugador_repository import JugadorRepository
from app.schemas import LoginRequest, RegistroRequest
from app.security import cifrar_contrasena, crear_token, verificar_contrasena


class CorreoYaRegistrado(Exception):
    """RN-01: el correo ya pertenece a otro jugador."""


class NombreUsuarioYaRegistrado(Exception):
    """RN-02: el nombre de usuario ya está en uso."""


class CredencialesInvalidas(Exception):
    """US-004: el usuario no existe o la contraseña no coincide."""


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

    def iniciar_sesion(self, datos: LoginRequest) -> tuple[Jugador, str]:
        """Devuelve el jugador y su token si el usuario (o correo) y la contraseña son correctos."""
        identificador = datos.usuario_o_correo.strip()
        jugador = self.repositorio.buscar_por_correo(
            identificador.lower()
        ) or self.repositorio.buscar_por_nombre_usuario(identificador)

        # Mismo error si el usuario no existe o si la contraseña está mal:
        # así nadie puede averiguar qué correos están registrados.
        if jugador is None or jugador.contrasena_hash is None:
            raise CredencialesInvalidas()
        if not verificar_contrasena(datos.contrasena, jugador.contrasena_hash):
            raise CredencialesInvalidas()

        return jugador, crear_token(jugador.id)