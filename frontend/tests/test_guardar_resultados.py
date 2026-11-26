"""El menú guarda en el ranking las partidas que terminó la arena."""
import json

import juego


class ClienteFalso:
    def __init__(self, falla=False):
        self.recibidas, self.falla = [], falla

    def guardar_partida_local(self, datos):
        if self.falla:
            raise ConnectionError("sin backend")
        self.recibidas.append(datos)
        return {"partida_id": 1, "duplicado": False}


def test_guarda_cada_partida_y_borra_el_archivo(tmp_path):
    archivo = tmp_path / "resultados.jsonl"
    archivo.write_text(json.dumps({"puntos": 40}) + "\n" + json.dumps({"puntos": 60}) + "\n")
    cliente = ClienteFalso()
    mensaje = juego.guardar_resultados(cliente, archivo)
    assert [d["puntos"] for d in cliente.recibidas] == [40, 60]
    assert "+100 puntos" in mensaje
    assert not archivo.exists()


def test_si_no_termino_ninguna_partida_no_muestra_nada(tmp_path):
    assert juego.guardar_resultados(ClienteFalso(), tmp_path / "no-existe.jsonl") is None


def test_sin_backend_avisa_que_no_se_guardo(tmp_path):
    archivo = tmp_path / "resultados.jsonl"
    archivo.write_text(json.dumps({"puntos": 40}) + "\n")
    assert juego.guardar_resultados(ClienteFalso(falla=True), archivo) == "No se pudo guardar la partida en el ranking"
