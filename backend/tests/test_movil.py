"""Pruebas de la versión web para celular (US-024)."""


def test_la_pagina_movil_se_sirve(client):
    respuesta = client.get("/movil/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "Control del Reactor" in respuesta.text
    assert 'name="viewport"' in respuesta.text  # se adapta a la pantalla del celular


def test_se_sirven_los_estilos_y_el_codigo(client):
    assert client.get("/movil/estilos.css").status_code == 200
    respuesta = client.get("/movil/app.js")
    assert respuesta.status_code == 200
    assert "/api/auth/login" in respuesta.text


def test_la_direccion_principal_lleva_al_celular(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code in (302, 307)
    assert respuesta.headers["location"] == "/movil/"


def test_la_pagina_tiene_todas_las_pantallas(client):
    html = client.get("/movil/").text
    for pantalla in ["login", "registro", "verificar", "recuperar", "menu", "perfil", "ranking"]:
        assert f'id="pantalla-{pantalla}"' in html


def test_se_sirve_el_juego_para_celular(client):
    """US-024: la pantalla Jugar trae la arena, las flechas y el botón de extraer."""
    respuesta = client.get("/movil/juego.js")
    assert respuesta.status_code == 200
    assert "/ws/partidas/" in respuesta.text
    pagina = client.get("/movil/").text
    for parte in ('id="arena"', 'data-direccion="ARRIBA"', 'id="extraer"', 'src="juego.js"'):
        assert parte in pagina
