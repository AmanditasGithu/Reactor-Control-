"""Pruebas de la verificación de correo (US-003)."""
import re
from datetime import datetime, timedelta, timezone

from app import config
from app.models import CodigoVerificacion, Jugador

REGISTRO = {"nombre_usuario": "ana_07", "correo": "ana@correo.com", "contrasena": "clave-segura-1"}


def registrar(client, capsys):
    """Registra a Ana y devuelve el código que le llegó por correo (impreso en la terminal)."""
    assert client.post("/api/auth/registro", json=REGISTRO).status_code == 201
    return leer_codigo(capsys)


def leer_codigo(capsys):
    encontrado = re.search(r"código de verificación es: (\d{6})", capsys.readouterr().out)
    return encontrado.group(1) if encontrado else None


def verificar(client, codigo, correo="ana@correo.com"):
    return client.post("/api/auth/verificar", json={"correo": correo, "codigo": codigo})


def login(client):
    return client.post(
        "/api/auth/login", json={"usuario_o_correo": "ana_07", "contrasena": "clave-segura-1"}
    )


def otro_codigo(codigo):
    return "000000" if codigo != "000000" else "111111"


def test_al_registrarse_llega_un_codigo(client, capsys):
    assert registrar(client, capsys) is not None


def test_verificar_con_codigo_correcto(client, capsys, db):
    codigo = registrar(client, capsys)

    respuesta = verificar(client, codigo)
    assert respuesta.status_code == 200
    assert db.query(Jugador).one().correo_verificado is True


def test_codigo_incorrecto_no_verifica(client, capsys, db):
    codigo = registrar(client, capsys)

    assert verificar(client, otro_codigo(codigo)).status_code == 400
    assert db.query(Jugador).one().correo_verificado is False


def test_codigo_vencido_da_error(client, capsys, db):
    codigo = registrar(client, capsys)
    registro = db.query(CodigoVerificacion).one()
    registro.vence = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert verificar(client, codigo).status_code == 400


def test_se_bloquea_despues_de_5_intentos(client, capsys):
    codigo = registrar(client, capsys)
    for _ in range(5):
        verificar(client, otro_codigo(codigo))

    assert verificar(client, codigo).status_code == 400


def test_reenviar_manda_un_codigo_nuevo_y_anula_el_anterior(client, capsys):
    primero = registrar(client, capsys)
    client.post("/api/auth/verificar/reenviar", json={"correo": "ana@correo.com"})
    segundo = leer_codigo(capsys)

    assert segundo is not None
    if primero != segundo:
        assert verificar(client, primero).status_code == 400
    assert verificar(client, segundo).status_code == 200


def test_reenviar_a_correo_no_registrado_responde_igual(client, capsys):
    respuesta = client.post("/api/auth/verificar/reenviar", json={"correo": "nadie@correo.com"})
    assert respuesta.status_code == 200
    assert "CORREO SIMULADO" not in capsys.readouterr().out


def test_login_sin_verificar_funciona_si_la_regla_esta_apagada(client, capsys, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_CORREO_VERIFICADO", False)
    registrar(client, capsys)
    assert login(client).status_code == 200


def test_login_sin_verificar_se_bloquea_si_la_regla_esta_encendida(client, capsys, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_CORREO_VERIFICADO", True)
    codigo = registrar(client, capsys)

    respuesta = login(client)
    assert respuesta.status_code == 403
    assert "Verificá tu correo" in respuesta.json()["detail"]

    verificar(client, codigo)
    assert login(client).status_code == 200


def test_el_codigo_se_guarda_cifrado(client, capsys, db):
    codigo = registrar(client, capsys)
    assert db.query(CodigoVerificacion).one().codigo_hash != codigo
