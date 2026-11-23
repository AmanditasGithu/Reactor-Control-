"""Conexión con Google y GitHub para el login con redes sociales (US-002).

Se usa OAuth 2.0 ("código de autorización"):
1. El jugador abre en el navegador la página de Google/GitHub (`url_de_autorizacion`).
2. Inicia sesión allá y acepta compartir su nombre y correo.
3. Google/GitHub lo mandan de vuelta al backend con un `code`.
4. El backend cambia ese `code` por los datos del jugador (`obtener_perfil`).

Usa solo la librería estándar (urllib), igual que el cliente del frontend.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app import config


class ErrorProveedor(Exception):
    """Google o GitHub rechazaron la petición, o no se pudo conectar con ellos."""


@dataclass
class PerfilSocial:
    """Lo que nos interesa de la cuenta de Google o GitHub del jugador."""

    proveedor_id: str  # id fijo de la cuenta en Google/GitHub
    correo: str | None
    correo_verificado: bool
    nombre: str  # se usa para inventar el nombre de usuario


def _pedir_json(url: str, datos: dict | None = None, token: str | None = None) -> dict | list:
    """Hace una petición (POST si hay datos, GET si no) y devuelve el JSON de la respuesta."""
    cuerpo = urllib.parse.urlencode(datos).encode("utf-8") if datos is not None else None
    peticion = urllib.request.Request(url, data=cuerpo)
    peticion.add_header("Accept", "application/json")
    peticion.add_header("User-Agent", "Control-del-Reactor")  # GitHub lo exige
    if token:
        peticion.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError) as error:
        raise ErrorProveedor(str(error)) from None


class ProveedorOAuth:
    """Lo común de Google y GitHub. Cada proveedor llena sus direcciones."""

    nombre = ""  # "google" o "github"
    nombre_visible = ""  # "Google" o "GitHub"
    url_autorizar = ""
    url_token = ""
    alcance = ""  # qué datos le pedimos al jugador (scope)

    @property
    def client_id(self) -> str:
        return getattr(config, f"{self.nombre.upper()}_CLIENT_ID")

    @property
    def client_secret(self) -> str:
        return getattr(config, f"{self.nombre.upper()}_CLIENT_SECRET")

    def configurado(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def url_de_autorizacion(self, state: str, redirect_uri: str) -> str:
        """Página de Google/GitHub donde el jugador inicia sesión."""
        parametros = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.alcance,
            "state": state,
        }
        return f"{self.url_autorizar}?{urllib.parse.urlencode(parametros)}"

    def _cambiar_code_por_token(self, code: str, redirect_uri: str) -> str:
        respuesta = _pedir_json(
            self.url_token,
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token = respuesta.get("access_token") if isinstance(respuesta, dict) else None
        if not token:
            raise ErrorProveedor(f"{self.nombre_visible} no entregó el token")
        return token

    def obtener_perfil(self, code: str, redirect_uri: str) -> PerfilSocial:
        raise NotImplementedError


class Google(ProveedorOAuth):
    nombre = "google"
    nombre_visible = "Google"
    url_autorizar = "https://accounts.google.com/o/oauth2/v2/auth"
    url_token = "https://oauth2.googleapis.com/token"
    url_perfil = "https://openidconnect.googleapis.com/v1/userinfo"
    alcance = "openid email profile"

    def url_de_autorizacion(self, state: str, redirect_uri: str) -> str:
        # "select_account" deja elegir la cuenta aunque ya haya una abierta en el navegador
        return super().url_de_autorizacion(state, redirect_uri) + "&prompt=select_account"

    def obtener_perfil(self, code: str, redirect_uri: str) -> PerfilSocial:
        token = self._cambiar_code_por_token(code, redirect_uri)
        datos = _pedir_json(self.url_perfil, token=token)
        if not isinstance(datos, dict) or "sub" not in datos:
            raise ErrorProveedor("Google no entregó los datos de la cuenta")
        correo = datos.get("email")
        return PerfilSocial(
            proveedor_id=str(datos["sub"]),
            correo=correo,
            correo_verificado=bool(datos.get("email_verified")),
            nombre=datos.get("name") or (correo or "").split("@")[0],
        )


class GitHub(ProveedorOAuth):
    nombre = "github"
    nombre_visible = "GitHub"
    url_autorizar = "https://github.com/login/oauth/authorize"
    url_token = "https://github.com/login/oauth/access_token"
    url_perfil = "https://api.github.com/user"
    url_correos = "https://api.github.com/user/emails"
    alcance = "read:user user:email"

    def obtener_perfil(self, code: str, redirect_uri: str) -> PerfilSocial:
        token = self._cambiar_code_por_token(code, redirect_uri)
        datos = _pedir_json(self.url_perfil, token=token)
        if not isinstance(datos, dict) or "id" not in datos:
            raise ErrorProveedor("GitHub no entregó los datos de la cuenta")

        # El correo de /user puede venir vacío si es privado: se pide la lista de correos
        # y se usa el principal, solo si GitHub ya lo verificó.
        correos = _pedir_json(self.url_correos, token=token)
        principal = next(
            (c for c in correos if isinstance(c, dict) and c.get("primary")),
            None,
        ) if isinstance(correos, list) else None
        return PerfilSocial(
            proveedor_id=str(datos["id"]),
            correo=principal.get("email") if principal else None,
            correo_verificado=bool(principal and principal.get("verified")),
            nombre=datos.get("login") or "",
        )


PROVEEDORES: dict[str, ProveedorOAuth] = {"google": Google(), "github": GitHub()}
