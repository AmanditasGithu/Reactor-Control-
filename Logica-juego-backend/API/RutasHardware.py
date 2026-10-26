
import os

from secrets import compare_digest
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from servicios.EstadoServidor import gestor, conexiones

router = APIRouter(
    prefix="/hardware",
    tags=["Hardware"]
)

class SenalAccion(BaseModel):
    id_partida: int
    id_jugador: int

    senal: Literal[
        "ACCION_PRESIONAR",
        "ACCION_SOLTAR",
        "ACCION_LATIDO"
    ]

@router.post("/accion")

async def recibir_accion(
    datos: SenalAccion,
    x_control_token: str = Header(default="")
):

    token_esperado = os.getenv(
        "CONTROL_HARDWARE_TOKEN", ""
    )

    if not token_esperado:
        raise HTTPException(
            status_code=503,
            detail="Token del hardware no configurado"
        )

    if not compare_digest(
        x_control_token,
        token_esperado
    ):
        raise HTTPException(
            status_code=401,
            detail="Control no autorizado"
        )

    resultado = gestor.procesar_senal_accion(
        datos.id_partida,
        datos.id_jugador,
        datos.senal
    )

    if resultado["cambio"]:
        estado = gestor.obtener_estado(
            datos.id_partida
        )

        await conexiones.enviar_a_partida(
            datos.id_partida,
            {
                "tipo": "estado",
                "partida": estado
            }
        )

    return resultado
