"""Pruebas del modelo de datos."""
import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.database import engine
from app.models import Jugador, Participacion, Partida


def test_se_crean_todas_las_tablas():
    tablas = set(inspect(engine).get_table_names())
    assert {"jugadores", "partidas", "participaciones", "eventos_partida", "records"} <= tablas


def test_no_permite_correo_duplicado(db):
    db.add(Jugador(nombre_usuario="ana", correo="ana@correo.com"))
    db.commit()
    db.add(Jugador(nombre_usuario="ana2", correo="ana@correo.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_no_permite_usuario_duplicado(db):
    db.add(Jugador(nombre_usuario="ana", correo="ana@correo.com"))
    db.commit()
    db.add(Jugador(nombre_usuario="ana", correo="otra@correo.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_participacion_relaciona_jugador_y_partida(db):
    jugador = Jugador(nombre_usuario="ana", correo="ana@correo.com")
    partida = Partida(escenario="laboratorio")
    db.add_all([jugador, partida])
    db.commit()

    db.add(Participacion(partida_id=partida.id, jugador_id=jugador.id, puntos=450, posicion=1))
    db.commit()
    db.refresh(jugador)

    assert jugador.participaciones[0].puntos == 450
    assert jugador.participaciones[0].partida.escenario == "laboratorio"


def test_health(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}