"""Lógica del login con redes sociales: Google y GitHub (US-002).

Como el juego es una app de escritorio (Pygame), el login pasa por el navegador:

    Juego                         Backend                         Google / GitHub
    ─────                         ───────                         ───────────────
    1. iniciar(proveedor) ──────► crea un InicioSocial
       ◄──────────── url + codigo_espera
    2. abre la url en el navegador ─────────────────────────────► el jugador inicia sesión
    3.                            callback(code, state) ◄──────── lo manda de vuelta
                                  busca o crea al jugador
    4. revisar(codigo_espera) ──► si ya terminó, entrega el token (una sola vez)

Los secretos de Google y GitHub solo los conoce el backend, nunca el juego.
"""
import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone

from app import config
from app.models import CuentaSocial, InicioSocial, Jugador
from app.oauth import PROVEEDORES, ErrorProveedor, ProveedorOAuth
from app.repositories.jugador_repository import JugadorRepository
from app.repositories.social_repository import SocialRepository
from app.security import cifrar_codigo, crear_token

MINUTOS_VALIDEZ = 10


class ProveedorDesconocido(Exception):
    """Se pidió un proveedor que no existe (ni google ni github)."""


class ProveedorNoConfigurado(Exception):
    """El proveedor existe, pero faltan su client id o su client secret en el .env."""


class InicioInvalido(Exception):
    """El inicio no existe, ya venció o ya se usó."""


def ruta_callback(proveedor: str) -> str:
    """Dirección a la que Google/GitHub mandan al jugador. Debe coincidir EXACTO con la
    que se registró en la app OAuth de cada proveedor."""
    return f"{config.URL_BACKEND}/api/auth/social/{proveedor}/callback"


def _ya_vencio(fecha: datetime) -> bool:
    if fecha.tzinfo is None:  # SQLite guarda las fechas sin zona horaria
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha < datetime.now(timezone.utc)


class SocialService:
    def __init__(
        self,
        jugadores: JugadorRepository,
        sociales: SocialRepository,
        proveedores: dict[str, ProveedorOAuth] | None = None,
    ):
        self.jugadores = jugadores
        self.sociales = sociales
        self.proveedores = proveedores if proveedores is not None else PROVEEDORES

    def _proveedor(self, nombre: str) -> ProveedorOAuth:
        proveedor = self.proveedores.get(nombre)
        if proveedor is None:
            raise ProveedorDesconocido()
        if not proveedor.configurado():
            raise ProveedorNoConfigurado()
        return proveedor

    # ── Paso 1 ────────────────────────────────────────────────────────────────
    def iniciar(self, nombre_proveedor: str) -> tuple[str, str]:
        """Crea un inicio de sesión. Devuelve (url para el navegador, codigo_espera)."""
        proveedor = self._proveedor(nombre_proveedor)
        state = secrets.token_urlsafe(32)
        codigo_espera = secrets.token_urlsafe(32)
        self.sociales.agregar(
            InicioSocial(
                proveedor=proveedor.nombre,
                state_hash=cifrar_codigo(state),
                espera_hash=cifrar_codigo(codigo_espera),
                vence=datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_VALIDEZ),
            )
        )
        self.sociales.guardar_cambios()
        url = proveedor.url_de_autorizacion(state, ruta_callback(proveedor.nombre))
        return url, codigo_espera

    # ── Paso 3 ────────────────────────────────────────────────────────────────
    def completar(
        self, nombre_proveedor: str, state: str | None, code: str | None, error: str | None
    ) -> Jugador:
        """Google/GitHub devolvieron al jugador. Devuelve el jugador que inició sesión.

        Si algo sale mal, lo anota en el inicio (para que el juego lo muestre) y lanza
        InicioInvalido con el mensaje para el navegador.
        """
        inicio = self.sociales.buscar_inicio_por_state(cifrar_codigo(state)) if state else None
        if (
            inicio is None
            or inicio.proveedor != nombre_proveedor
            or inicio.jugador_id is not None
            or inicio.error is not None
            or _ya_vencio(inicio.vence)
        ):
            raise InicioInvalido("Este enlace ya venció o ya se usó. Volvé al juego e intentá de nuevo.")

        proveedor = self._proveedor(nombre_proveedor)
        if error or not code:
            return self._fallar(inicio, "Cancelaste el inicio de sesión")

        try:
            perfil = proveedor.obtener_perfil(code, ruta_callback(proveedor.nombre))
        except ErrorProveedor:
            return self._fallar(inicio, f"No se pudo conectar con {proveedor.nombre_visible}")

        if not perfil.correo or not perfil.correo_verificado:
            return self._fallar(
                inicio, f"Tu cuenta de {proveedor.nombre_visible} no tiene un correo verificado"
            )

        jugador = self._buscar_o_crear_jugador(proveedor.nombre, perfil)
        inicio.jugador_id = jugador.id
        self.sociales.guardar_cambios()
        return jugador

    def _fallar(self, inicio: InicioSocial, mensaje: str):
        inicio.error = mensaje
        self.sociales.guardar_cambios()
        raise InicioInvalido(mensaje)

    def _buscar_o_crear_jugador(self, proveedor: str, perfil) -> Jugador:
        # 1. Ya había entrado antes con esta misma cuenta de Google/GitHub
        cuenta = self.sociales.buscar_cuenta(proveedor, perfil.proveedor_id)
        if cuenta is not None:
            jugador = self.jugadores.buscar_por_id(cuenta.jugador_id)
            if jugador is not None:
                return jugador

        # 2. Ya tiene cuenta en el juego con ese correo: se le une la red social.
        #    Es seguro porque Google/GitHub confirmaron que el correo es suyo.
        correo = perfil.correo.lower()
        jugador = self.jugadores.buscar_por_correo(correo)

        # 3. Es nuevo: se crea la cuenta sin contraseña (RN-01 y RN-02 se respetan)
        if jugador is None:
            jugador = Jugador(
                nombre_usuario=self._nombre_libre(perfil.nombre or correo.split("@")[0]),
                correo=correo,
                contrasena_hash=None,
                proveedor=proveedor,
                correo_verificado=True,
            )
            self.jugadores.guardar(jugador)

        elif not jugador.correo_verificado:
            # Alguien creó esta cuenta con el correo del jugador pero nunca lo verificó.
            # Podría ser otra persona que la preparó para robarla, así que su contraseña
            # se borra: desde ahora solo se entra con la red social que probó ser dueña.
            jugador.contrasena_hash = None

        jugador.correo_verificado = True
        if cuenta is None:
            self.sociales.agregar(
                CuentaSocial(jugador_id=jugador.id, proveedor=proveedor, proveedor_id=perfil.proveedor_id)
            )
        else:
            cuenta.jugador_id = jugador.id
        self.sociales.guardar_cambios()
        return jugador

    def _nombre_libre(self, nombre: str) -> str:
        """Convierte "José Pérez" en "Jose_Perez" y, si ya existe, prueba Jose_Perez2, 3..."""
        sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
        base = re.sub(r"[^A-Za-z0-9_]+", "_", sin_tildes).strip("_")[:25]
        if len(base) < 3:
            base = "jugador"
        candidato, numero = base, 2
        while self.jugadores.buscar_por_nombre_usuario(candidato):
            candidato = f"{base}{numero}"
            numero += 1
        return candidato

    # ── Paso 4 ────────────────────────────────────────────────────────────────
    def revisar(self, codigo_espera: str) -> tuple[str, Jugador | None, str | None]:
        """El juego pregunta si el jugador ya terminó en el navegador.

        Devuelve (estado, jugador, token_o_mensaje):
        - ("pendiente", None, None): todavía no termina
        - ("listo", jugador, token): ya puede entrar (el token se entrega una sola vez)
        - ("error", None, mensaje): algo salió mal
        """
        inicio = self.sociales.buscar_inicio_por_espera(cifrar_codigo(codigo_espera))
        if inicio is None or inicio.usado:
            raise InicioInvalido("El inicio de sesión no existe o ya se usó")
        if inicio.error:
            inicio.usado = True
            self.sociales.guardar_cambios()
            return "error", None, inicio.error
        if inicio.jugador_id is None:
            if _ya_vencio(inicio.vence):
                inicio.usado = True
                self.sociales.guardar_cambios()
                return "error", None, "Se acabó el tiempo. Intentá de nuevo"
            return "pendiente", None, None

        jugador = self.jugadores.buscar_por_id(inicio.jugador_id)
        inicio.usado = True
        self.sociales.guardar_cambios()
        return "listo", jugador, crear_token(jugador.id)
