from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from modelos.Jugador import Jugador
from servicios.EstadoServidor import gestor, conexiones

router = APIRouter(prefix = "/partidas", tags = ["Partidas"])

class DatosJugador(BaseModel):
    id_jugador: int = Field(gt=0)
    nombre: str = Field(min_length = 1, max_length = 50)

@router.post("", status_code = status.HTTP_201_CREATED)

def crear_partida():
    partida = gestor.crear_partida()

    return {
        "mensaje": "Partida creada correctamente",
        "id_partida": partida.id_partida,
        "estado": partida.estado
    }

@router.get("")

def listar_partidas():
    return gestor.listar_partidas()

@router.get("/{id_partida}")

def obtener_partida(id_partida: int):
    partida = gestor.obtener_partida(id_partida)

    if partida is None:
        raise HTTPException(
            status_code = 404,
            detail = "La partida no existe"
        )

    jugadores = []

    for jugador in partida.jugadores:
        
        informacion = {
            "id_jugador": jugador.id_jugador,
            "nombre": jugador.nombre,
            "x": jugador.x,
            "y": jugador.y,
            "puntos": jugador.puntos
        }

        jugadores.append(informacion)

    return {
        "id_partida": partida.id_partida,
        "estado": partida.estado,
        "jugadores": jugadores
    }

@router.post("/{id_partida}/unirse")
def unir_jugador(id_partida: int, datos: DatosJugador):
    partida = gestor.obtener_partida(id_partida)

    if partida is None:

        raise HTTPException(
            status_code = 404,
            detail = "La partida no existe"
        )

    jugador = Jugador(
        datos.id_jugador
        datos.nombre
    )

    resultado = gestor.unir_jugador(
        id_partida,
        jugador
    )

    if not resultado:
        raise HTTPException(
            status_code = 409,
            detail = "No se puede unir el jugador a esta partida"
        )

    return {
        "mensaje": "Jugador unido correctamente",
        "id_partida": id_partida,
        "id_jugador": jugador.id_jugador,
        "nombre": jugador.nombre
    }

@router.post("/{id_partida}/iniciar")

async def iniciar_partida(id_partida: int):
    partida = gestor.obtener_partida(id_partida)

    if partida is None:
        raise HTTPException(
            status_code = 404,
            detail = "La partida no existe"
        )

    resultado = gestor.iniciar_partida(id_partida)

    if not resultado:
        raise HTTPException(
            status_code = 409,
            detail = "La partida no puede iniciarse"
        )

    await conexiones.enviar_a_partida(
        id_partida,
        {
            "tipo": "estado",
            "partida": gestor.obtener_estado(id_partida)
        }
    )


    return {
        "mensaje": "Partida iniciada correctamente",
        "id_partida": id_partida,
        "estado": partida.estado
    }