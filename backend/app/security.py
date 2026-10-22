"""Cifrado de contraseñas (RNF-04)."""
import bcrypt


def cifrar_contrasena(contrasena: str) -> str:
    """Devuelve la contraseña cifrada con bcrypt, lista para guardar."""
    return bcrypt.hashpw(contrasena.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_contrasena(contrasena: str, contrasena_hash: str) -> bool:
    """Revisa si una contraseña coincide con la versión cifrada guardada."""
    return bcrypt.checkpw(contrasena.encode("utf-8"), contrasena_hash.encode("utf-8"))