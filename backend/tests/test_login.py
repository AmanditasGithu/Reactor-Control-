"""Pruebas del inicio de sesión (US-004)."""
from app.security import crear_token

REGISTRO = {"nombre_usuario": "ana_07", "correo": "ana@correo.com", "contrasena": "clave-segura-1"}


def registrar_ana(client):
    client.post("/api/auth/registro", json=REGISTRO)


def login(client, usuario_o_correo, contrasena):
    return client.post(
        "/api/auth/login",
        json={"usuario_o_correo": usuario_o_correo, "contrasena": contrasena},
    )


def test_login_con_correo(client):
    registrar_ana(client)
    respuesta = login(client, "ana@correo.com", "clave-segura-1")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["access_token"]
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["jugador"]["nombre_usuario"] == "ana_07"


def test_login_con_nombre_de_usuario(client):
    registrar_ana(client)
    assert login(client, "ana_07", "clave-segura-1").status_code == 200


def test_login_con_correo_en_mayusculas(client):
    registrar_ana(client)
    assert login(client, "ANA@Correo.com", "clave-segura-1").status_code == 200


def test_contrasena_incorrecta_da_error(client):
    registrar_ana(client)
    respuesta = login(client, "ana@correo.com", "otra-clave")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario, correo o contraseña incorrectos"


def test_usuario_inexistente_da_el_mismo_error(client):
    respuesta = login(client, "nadie@correo.com", "clave-segura-1")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Usuario, correo o contraseña incorrectos"


def test_token_permite_ver_quien_soy(client):
    registrar_ana(client)
    token = login(client, "ana_07", "clave-segura-1").json()["access_token"]

    respuesta = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre_usuario"] == "ana_07"


def test_quien_soy_sin_token_da_error(client):
    assert client.get("/api/auth/yo").status_code == 401


def test_quien_soy_con_token_falso_da_error(client):
    respuesta = client.get("/api/auth/yo", headers={"Authorization": "Bearer token-inventado"})
    assert respuesta.status_code == 401


def test_token_de_jugador_inexistente_da_error(client):
    token = crear_token(999)
    respuesta = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401