"""Pruebas de recuperar la contraseña (US-005)."""
import re
from datetime import datetime, timedelta, timezone

from app.models import CodigoRecuperacion

REGISTRO = {"nombre_usuario": "ana_07", "correo": "ana@correo.com", "contrasena": "clave-vieja-1"}


def pedir_codigo(client, capsys, correo="ana@correo.com"):
    """Pide el código y lo lee del 'correo' que el backend imprime en la terminal."""
    respuesta = client.post("/api/auth/recuperar/solicitar", json={"correo": correo})
    assert respuesta.status_code == 200
    encontrado = re.search(r"tu código es: (\d{6})", capsys.readouterr().out)
    return encontrado.group(1) if encontrado else None


def restablecer(client, codigo, contrasena="clave-nueva-1", correo="ana@correo.com"):
    return client.post(
        "/api/auth/recuperar/restablecer",
        json={"correo": correo, "codigo": codigo, "contrasena_nueva": contrasena},
    )


def login(client, contrasena):
    return client.post(
        "/api/auth/login", json={"usuario_o_correo": "ana_07", "contrasena": contrasena}
    )


def test_recuperar_contrasena_completo(client, capsys):
    client.post("/api/auth/registro", json=REGISTRO)
    codigo = pedir_codigo(client, capsys)

    assert codigo is not None
    assert restablecer(client, codigo).status_code == 200
    assert login(client, "clave-nueva-1").status_code == 200
    assert login(client, "clave-vieja-1").status_code == 401


def test_correo_no_registrado_responde_igual_y_no_envia_nada(client, capsys):
    respuesta = client.post("/api/auth/recuperar/solicitar", json={"correo": "nadie@correo.com"})
    assert respuesta.status_code == 200
    assert "CORREO SIMULADO" not in capsys.readouterr().out


def test_codigo_incorrecto_da_error(client, capsys):
    client.post("/api/auth/registro", json=REGISTRO)
    codigo = pedir_codigo(client, capsys)
    otro = "000000" if codigo != "000000" else "111111"

    respuesta = restablecer(client, otro)
    assert respuesta.status_code == 400
    assert login(client, "clave-vieja-1").status_code == 200  # la contraseña no cambió


def test_codigo_sirve_una_sola_vez(client, capsys):
    client.post("/api/auth/registro", json=REGISTRO)
    codigo = pedir_codigo(client, capsys)

    assert restablecer(client, codigo).status_code == 200
    assert restablecer(client, codigo, "otra-clave-2").status_code == 400


def test_pedir_otro_codigo_anula_el_anterior(client, capsys):
    client.post("/api/auth/registro", json=REGISTRO)
    primero = pedir_codigo(client, capsys)
    segundo = pedir_codigo(client, capsys)

    if primero != segundo:
        assert restablecer(client, primero).status_code == 400
    assert restablecer(client, segundo).status_code == 200


def test_codigo_vencido_da_error(client, capsys, db):
    client.post("/api/auth/registro", json=REGISTRO)
    codigo = pedir_codigo(client, capsys)
    registro = db.query(CodigoRecuperacion).one()
    registro.vence = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert restablecer(client, codigo).status_code == 400


def test_se_bloquea_despues_de_5_intentos(client, capsys):
    client.post("/api/auth/registro", json=REGISTRO)
    codigo = pedir_codigo(client, capsys)
    malo = "000000" if codigo != "000000" else "111111"
    for _ in range(5):
        restablecer(client, malo)

    assert restablecer(client, codigo).status_code == 400  # ni el correcto sirve ya


def test_el_codigo_se_guarda_cifrado(client, capsys, db):
    client.post("/api/auth/registro", json=REGISTRO)
    codigo = pedir_codigo(client, capsys)
    assert db.query(CodigoRecuperacion).one().codigo_hash != codigo


def test_datos_invalidos_dan_422(client):
    assert restablecer(client, "12ab").status_code == 422  # el código son 6 números
    assert restablecer(client, "123456", "corta").status_code == 422
