"""Conexión entre las pantallas (Pygame) y el backend (API de FastAPI).

Usa solo la librería estándar de Python (urllib), así no hay que instalar nada extra.
"""
import json
import os
import urllib.error
import urllib.request

# Dirección del backend. Se puede cambiar con la variable de entorno REACTOR_API_URL.
API_URL = os.getenv("REACTOR_API_URL", "http://localhost:8000")


class ErrorAPI(Exception):
    """El backend respondió con un error, o no se pudo conectar con él."""

    def __init__(self, mensaje: str, codigo: int | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


# Mensajes en español para los errores de validación (422) que manda el backend
MENSAJES_CAMPOS = {
    "nombre_usuario": "El usuario debe tener de 3 a 30 caracteres: letras, números o _",
    "correo": "Escribí un correo válido (ejemplo: ana@correo.com)",
    "contrasena": "La contraseña debe tener al menos 8 caracteres",
    "usuario_o_correo": "Escribí tu usuario o correo",
}


class ClienteAPI:
    """Envía peticiones al backend y devuelve las respuestas como diccionarios."""

    def __init__(self, url_base: str = API_URL):
        self.url_base = url_base.rstrip("/")
        self.token: str | None = None  # se guarda al iniciar sesión

    def _enviar(self, metodo: str, ruta: str, datos: dict | None = None) -> dict:
        cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
        peticion = urllib.request.Request(self.url_base + ruta, data=cuerpo, method=metodo)
        peticion.add_header("Content-Type", "application/json")
        if self.token:
            peticion.add_header("Authorization", f"Bearer {self.token}")

        try:
            with urllib.request.urlopen(peticion, timeout=5) as respuesta:
                return json.loads(respuesta.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise ErrorAPI(self._mensaje_de_error(error), error.code) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            raise ErrorAPI("No se pudo conectar con el servidor. ¿Está encendido?") from None

    @staticmethod
    def _mensaje_de_error(error: urllib.error.HTTPError) -> str:
        try:
            detalle = json.loads(error.read().decode("utf-8")).get("detail")
        except (ValueError, AttributeError):
            return "Ocurrió un error en el servidor"

        if isinstance(detalle, str):  # 401 y 409 traen un mensaje listo
            return detalle
        if isinstance(detalle, list) and detalle:  # 422: datos inválidos
            campo = detalle[0].get("loc", [None])[-1]
            return MENSAJES_CAMPOS.get(campo, "Revisá los datos ingresados")
        return "Ocurrió un error en el servidor"

    def registrar(self, nombre_usuario: str, correo: str, contrasena: str) -> dict:
        """US-001: crea la cuenta. Devuelve los datos del jugador."""
        return self._enviar(
            "POST",
            "/api/auth/registro",
            {"nombre_usuario": nombre_usuario, "correo": correo, "contrasena": contrasena},
        )

    def iniciar_sesion(self, usuario_o_correo: str, contrasena: str) -> dict:
        """US-004: inicia sesión. Guarda el token y devuelve los datos del jugador."""
        respuesta = self._enviar(
            "POST",
            "/api/auth/login",
            {"usuario_o_correo": usuario_o_correo, "contrasena": contrasena},
        )
        self.token = respuesta["access_token"]
        return respuesta["jugador"]
