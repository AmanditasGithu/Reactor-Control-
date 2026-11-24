"""Pruebas del login con redes sociales (US-002).

No se conecta con Google ni GitHub de verdad: `obtener_perfil` se reemplaza por
una función falsa que devuelve el perfil que la prueba quiera.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app import config
from app.models import CuentaSocial, InicioSocial, Jugador
from app.oauth import PROVEEDORES, ErrorProveedor, PerfilSocial

PERFIL_ANA = PerfilSocial(
    proveedor_id="google-123", correo="Ana@Gmail.com", correo_verificado=True, nombre="Ana Pérez"
)


@pytest.fixture(autouse=True)
def proveedores_configurados(monkeypatch):
    """Simula que el .env tiene los client id y secret de Google y GitHub."""
    for nombre in ("GOOGLE", "GITHUB"):
        monkeypatch.setattr(config, f"{nombre}_CLIENT_ID", f"id-{nombre.lower()}")
        monkeypatch.setattr(config, f"{nombre}_CLIENT_SECRET", f"secreto-{nombre.lower()}")


@pytest.fixture
def perfil(monkeypatch):
    """Cambia lo que "responde" Google/GitHub. Uso: perfil(PerfilSocial(...)) o perfil(error)."""
    recibidos = []

    def usar(respuesta, proveedor="google"):
        def obtener_perfil(code, redirect_uri):
            recibidos.append((code, redirect_uri))
            if isinstance(respuesta, Exception):
                raise respuesta
            return respuesta

        monkeypatch.setattr(PROVEEDORES[proveedor], "obtener_perfil", obtener_perfil)
        return recibidos

    return usar


def iniciar(client, proveedor="google"):
    respuesta = client.post(f"/api/auth/social/{proveedor}/iniciar")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    state = parse_qs(urlparse(cuerpo["url"]).query)["state"][0]
    return cuerpo, state


def volver(client, state, proveedor="google", **parametros):
    """Simula que Google/GitHub mandan al jugador de vuelta al backend."""
    parametros.setdefault("code", "codigo-de-google")
    return client.get(f"/api/auth/social/{proveedor}/callback", params={"state": state, **parametros})


def revisar(client, codigo_espera):
    return client.post("/api/auth/social/revisar", json={"codigo_espera": codigo_espera})


def login_completo(client, proveedor="google"):
    cuerpo, state = iniciar(client, proveedor)
    assert volver(client, state, proveedor).status_code == 200
    return revisar(client, cuerpo["codigo_espera"]).json()


# ── Paso 1: iniciar ─────────────────────────────────────────────────────────────

def test_iniciar_devuelve_la_pagina_de_google(client):
    cuerpo, _ = iniciar(client)
    url = urlparse(cuerpo["url"])
    parametros = parse_qs(url.query)

    assert url.netloc == "accounts.google.com"
    assert parametros["client_id"] == ["id-google"]
    assert parametros["redirect_uri"] == ["http://localhost:8000/api/auth/social/google/callback"]
    assert "email" in parametros["scope"][0]
    assert cuerpo["codigo_espera"]


def test_iniciar_con_github(client):
    cuerpo, _ = iniciar(client, "github")
    assert urlparse(cuerpo["url"]).netloc == "github.com"


def test_el_secreto_nunca_sale_del_backend(client):
    cuerpo, _ = iniciar(client)
    assert "secreto" not in cuerpo["url"]


def test_state_y_codigo_espera_son_distintos(client):
    cuerpo, state = iniciar(client)
    assert state != cuerpo["codigo_espera"]


def test_state_y_codigo_espera_se_guardan_cifrados(client, db):
    cuerpo, state = iniciar(client)
    inicio = db.query(InicioSocial).one()
    assert inicio.state_hash != state
    assert inicio.espera_hash != cuerpo["codigo_espera"]


def test_proveedor_que_no_existe(client):
    assert client.post("/api/auth/social/facebook/iniciar").status_code == 404


def test_proveedor_sin_configurar(client, monkeypatch):
    monkeypatch.setattr(config, "GOOGLE_CLIENT_SECRET", "")
    respuesta = client.post("/api/auth/social/google/iniciar")

    assert respuesta.status_code == 503
    assert "no está configurado" in respuesta.json()["detail"]


# ── Pasos 3 y 4: volver del navegador y recoger el token ───────────────────────

def test_mientras_no_termina_sigue_pendiente(client):
    cuerpo, _ = iniciar(client)
    respuesta = revisar(client, cuerpo["codigo_espera"])

    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "pendiente"


def test_jugador_nuevo_con_google(client, perfil, db):
    recibidos = perfil(PERFIL_ANA)
    cuerpo, state = iniciar(client)

    pagina = volver(client, state)
    assert pagina.status_code == 200
    assert "volver al juego" in pagina.text

    respuesta = revisar(client, cuerpo["codigo_espera"]).json()
    assert respuesta["estado"] == "listo"
    assert respuesta["access_token"]
    assert respuesta["jugador"]["nombre_usuario"] == "Ana_Perez"
    assert respuesta["jugador"]["correo"] == "ana@gmail.com"
    assert respuesta["jugador"]["correo_verificado"] is True

    # Se le pasó a Google el mismo redirect_uri del paso 1 (si no, Google lo rechaza)
    assert recibidos == [("codigo-de-google", "http://localhost:8000/api/auth/social/google/callback")]

    jugador = db.query(Jugador).one()
    assert jugador.contrasena_hash is None
    assert jugador.proveedor == "google"


def test_el_token_sirve_para_la_api(client, perfil):
    perfil(PERFIL_ANA)
    token = login_completo(client)["access_token"]

    respuesta = client.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == "ana@gmail.com"


def test_el_token_se_entrega_una_sola_vez(client, perfil):
    perfil(PERFIL_ANA)
    cuerpo, state = iniciar(client)
    volver(client, state)

    assert revisar(client, cuerpo["codigo_espera"]).json()["estado"] == "listo"
    assert revisar(client, cuerpo["codigo_espera"]).status_code == 404


def test_segunda_vez_entra_a_la_misma_cuenta(client, perfil, db):
    perfil(PERFIL_ANA)
    primera = login_completo(client)
    segunda = login_completo(client)

    assert primera["jugador"]["id"] == segunda["jugador"]["id"]
    assert db.query(Jugador).count() == 1
    assert db.query(CuentaSocial).count() == 1


def test_si_ya_tenia_cuenta_con_ese_correo_se_unen(client, perfil, db):
    client.post(
        "/api/auth/registro",
        json={"nombre_usuario": "ana_07", "correo": "ana@gmail.com", "contrasena": "clave-segura-1"},
    )
    db.query(Jugador).one().correo_verificado = True  # Ana ya había verificado su correo
    db.commit()
    perfil(PERFIL_ANA)
    respuesta = login_completo(client)

    assert respuesta["jugador"]["nombre_usuario"] == "ana_07"
    assert db.query(Jugador).count() == 1
    # Y la contraseña sigue sirviendo
    login = client.post(
        "/api/auth/login", json={"usuario_o_correo": "ana_07", "contrasena": "clave-segura-1"}
    )
    assert login.status_code == 200


def test_cuenta_preparada_por_otro_pierde_su_contrasena(client, perfil, db):
    """Alguien registró el correo de Ana sin verificarlo. Cuando Ana entra con Google,
    la contraseña de esa persona deja de servir."""
    client.post(
        "/api/auth/registro",
        json={"nombre_usuario": "ladron", "correo": "ana@gmail.com", "contrasena": "clave-del-ladron"},
    )
    perfil(PERFIL_ANA)
    respuesta = login_completo(client)

    assert respuesta["jugador"]["correo_verificado"] is True
    login = client.post(
        "/api/auth/login", json={"usuario_o_correo": "ladron", "contrasena": "clave-del-ladron"}
    )
    assert login.status_code == 401


def test_google_y_github_del_mismo_correo_son_la_misma_cuenta(client, perfil, db):
    perfil(PERFIL_ANA, "google")
    perfil(
        PerfilSocial(proveedor_id="99", correo="ana@gmail.com", correo_verificado=True, nombre="ana-dev"),
        "github",
    )
    con_google = login_completo(client, "google")
    con_github = login_completo(client, "github")

    assert con_google["jugador"]["id"] == con_github["jugador"]["id"]
    assert db.query(CuentaSocial).count() == 2


def test_nombre_de_usuario_repetido_recibe_un_numero(client, perfil):
    client.post(
        "/api/auth/registro",
        json={"nombre_usuario": "Ana_Perez", "correo": "otra@correo.com", "contrasena": "clave-segura-1"},
    )
    perfil(PERFIL_ANA)
    assert login_completo(client)["jugador"]["nombre_usuario"] == "Ana_Perez2"


def test_nombre_muy_corto_o_raro(client, perfil):
    perfil(PerfilSocial(proveedor_id="1", correo="x@correo.com", correo_verificado=True, nombre="李"))
    assert login_completo(client)["jugador"]["nombre_usuario"] == "jugador"


# ── Cuando algo sale mal ───────────────────────────────────────────────────────

def test_correo_sin_verificar_no_entra(client, perfil, db):
    perfil(PerfilSocial(proveedor_id="1", correo="ana@gmail.com", correo_verificado=False, nombre="Ana"))
    cuerpo, state = iniciar(client)

    assert volver(client, state).status_code == 400
    respuesta = revisar(client, cuerpo["codigo_espera"]).json()
    assert respuesta["estado"] == "error"
    assert "correo verificado" in respuesta["mensaje"]
    assert db.query(Jugador).count() == 0


def test_correo_sin_verificar_no_se_apropia_de_otra_cuenta(client, perfil):
    """Si alguien pone el correo de Ana en GitHub sin verificarlo, no entra a la cuenta de Ana."""
    client.post(
        "/api/auth/registro",
        json={"nombre_usuario": "ana_07", "correo": "ana@gmail.com", "contrasena": "clave-segura-1"},
    )
    perfil(
        PerfilSocial(proveedor_id="666", correo="ana@gmail.com", correo_verificado=False, nombre="x"),
        "github",
    )
    cuerpo, state = iniciar(client, "github")
    assert volver(client, state, "github").status_code == 400
    assert revisar(client, cuerpo["codigo_espera"]).json()["estado"] == "error"


def test_jugador_cancela_en_google(client):
    cuerpo, state = iniciar(client)
    pagina = client.get(
        "/api/auth/social/google/callback", params={"state": state, "error": "access_denied"}
    )

    assert pagina.status_code == 400
    respuesta = revisar(client, cuerpo["codigo_espera"]).json()
    assert respuesta == {**respuesta, "estado": "error", "mensaje": "Cancelaste el inicio de sesión"}


def test_google_no_responde(client, perfil):
    perfil(ErrorProveedor("sin internet"))
    cuerpo, state = iniciar(client)
    volver(client, state)

    respuesta = revisar(client, cuerpo["codigo_espera"]).json()
    assert respuesta["estado"] == "error"
    assert "No se pudo conectar con Google" in respuesta["mensaje"]


def test_state_inventado_no_sirve(client, perfil):
    perfil(PERFIL_ANA)
    pagina = volver(client, "state-inventado")
    assert pagina.status_code == 400
    assert "venció" in pagina.text


def test_el_enlace_del_navegador_sirve_una_sola_vez(client, perfil):
    perfil(PERFIL_ANA)
    _, state = iniciar(client)
    assert volver(client, state).status_code == 200
    assert volver(client, state).status_code == 400


def test_state_de_google_no_sirve_en_github(client, perfil):
    perfil(PERFIL_ANA, "github")
    _, state = iniciar(client, "google")
    assert volver(client, state, "github").status_code == 400


def test_inicio_vencido(client, perfil, db):
    perfil(PERFIL_ANA)
    cuerpo, state = iniciar(client)
    inicio = db.query(InicioSocial).one()
    inicio.vence = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert volver(client, state).status_code == 400
    respuesta = revisar(client, cuerpo["codigo_espera"]).json()
    assert respuesta["estado"] == "error"


def test_codigo_espera_inventado(client):
    assert revisar(client, "codigo-que-no-existe").status_code == 404


def test_la_pagina_no_ejecuta_html_del_nombre(client, perfil):
    perfil(
        PerfilSocial(proveedor_id="1", correo="h@correo.com", correo_verificado=True, nombre="<script>x"),
    )
    _, state = iniciar(client)
    assert "<script>" not in volver(client, state).text


def test_cuenta_creada_con_google_no_entra_con_contrasena(client, perfil):
    """Una cuenta creada con Google no tiene contraseña: no entra por el login normal."""
    perfil(PERFIL_ANA)
    nombre = login_completo(client)["jugador"]["nombre_usuario"]
    login = client.post("/api/auth/login", json={"usuario_o_correo": nombre, "contrasena": "lo-que-sea"})
    assert login.status_code == 401


# ── Cómo se leen las respuestas reales de Google y GitHub ──────────────────────

def respuestas_falsas(monkeypatch, respuestas: dict):
    """Reemplaza las peticiones a internet: cada URL responde lo que diga el diccionario."""
    pedidas = []

    def pedir_json(url, datos=None, token=None):
        pedidas.append((url, datos, token))
        return respuestas[url]

    monkeypatch.setattr("app.oauth._pedir_json", pedir_json)
    return pedidas


def test_google_lee_el_perfil(monkeypatch):
    google = PROVEEDORES["google"]
    pedidas = respuestas_falsas(monkeypatch, {
        google.url_token: {"access_token": "tok"},
        google.url_perfil: {"sub": "123", "email": "ana@gmail.com", "email_verified": True, "name": "Ana"},
    })
    perfil = google.obtener_perfil("code-1", "http://x/callback")

    assert perfil == PerfilSocial("123", "ana@gmail.com", True, "Ana")
    url, datos, _ = pedidas[0]
    assert datos["client_secret"] == "secreto-google" and datos["code"] == "code-1"
    assert pedidas[1][2] == "tok"


def test_github_usa_el_correo_principal_verificado(monkeypatch):
    github = PROVEEDORES["github"]
    respuestas_falsas(monkeypatch, {
        github.url_token: {"access_token": "tok"},
        github.url_perfil: {"id": 42, "login": "ana-dev", "email": None},
        github.url_correos: [
            {"email": "viejo@correo.com", "primary": False, "verified": True},
            {"email": "ana@gmail.com", "primary": True, "verified": True},
        ],
    })
    assert github.obtener_perfil("c", "r") == PerfilSocial("42", "ana@gmail.com", True, "ana-dev")


def test_github_con_correo_principal_sin_verificar(monkeypatch):
    github = PROVEEDORES["github"]
    respuestas_falsas(monkeypatch, {
        github.url_token: {"access_token": "tok"},
        github.url_perfil: {"id": 42, "login": "ana-dev"},
        github.url_correos: [{"email": "ana@gmail.com", "primary": True, "verified": False}],
    })
    assert github.obtener_perfil("c", "r").correo_verificado is False


def test_code_rechazado_por_el_proveedor(monkeypatch):
    github = PROVEEDORES["github"]
    respuestas_falsas(monkeypatch, {github.url_token: {"error": "bad_verification_code"}})
    with pytest.raises(ErrorProveedor):
        github.obtener_perfil("c", "r")
