"""Pruebas del registro de jugadores (US-001)."""
from app.models import Jugador
from app.security import verificar_contrasena

URL = "/api/auth/registro"
DATOS = {"nombre_usuario": "ana_07", "correo": "ana@correo.com", "contrasena": "clave-segura-1"}


def test_registro_exitoso(client):
    respuesta = client.post(URL, json=DATOS)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["nombre_usuario"] == "ana_07"
    assert cuerpo["correo"] == "ana@correo.com"
    assert cuerpo["correo_verificado"] is False


def test_respuesta_no_incluye_contrasena(client):
    cuerpo = client.post(URL, json=DATOS).json()
    assert "contrasena" not in cuerpo
    assert "contrasena_hash" not in cuerpo


def test_contrasena_se_guarda_cifrada(client, db):
    client.post(URL, json=DATOS)
    jugador = db.query(Jugador).filter_by(nombre_usuario="ana_07").one()

    assert jugador.contrasena_hash != "clave-segura-1"  # RNF-04
    assert verificar_contrasena("clave-segura-1", jugador.contrasena_hash)


def test_correo_duplicado_da_error(client):
    client.post(URL, json=DATOS)
    otro = {**DATOS, "nombre_usuario": "otra_ana"}

    respuesta = client.post(URL, json=otro)
    assert respuesta.status_code == 409  # RN-01
    assert "correo" in respuesta.json()["detail"]


def test_correo_duplicado_con_mayusculas_da_error(client):
    client.post(URL, json=DATOS)
    otro = {**DATOS, "nombre_usuario": "otra_ana", "correo": "ANA@Correo.com"}

    assert client.post(URL, json=otro).status_code == 409


def test_nombre_usuario_duplicado_da_error(client):
    client.post(URL, json=DATOS)
    otro = {**DATOS, "correo": "otra@correo.com"}

    respuesta = client.post(URL, json=otro)
    assert respuesta.status_code == 409  # RN-02
    assert "usuario" in respuesta.json()["detail"]


def test_correo_invalido_da_error(client):
    respuesta = client.post(URL, json={**DATOS, "correo": "esto-no-es-un-correo"})
    assert respuesta.status_code == 422


def test_contrasena_corta_da_error(client):
    respuesta = client.post(URL, json={**DATOS, "contrasena": "123"})
    assert respuesta.status_code == 422


def test_nombre_usuario_con_espacios_da_error(client):
    respuesta = client.post(URL, json={**DATOS, "nombre_usuario": "ana maria"})
    assert respuesta.status_code == 422