"""US-023: bandeja de salida durable para resultados de partidas finalizadas.

No realiza peticiones desde el hilo de juego: persiste en SQLite y un
worker independiente reintenta enviarlas a la API de cuentas/PostgreSQL.
"""
import json
import logging
import os
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path

LOG = logging.getLogger(__name__)


class EnvioResultados:
    def __init__(self, archivo=None, url=None, token=None):
        self.archivo = str(archivo or os.getenv("REACTOR_BANDEJA_RESULTADOS", "./datos/resultados_pendientes.sqlite3"))
        self.url = url or os.getenv("REACTOR_URL_RECEPCION_RESULTADOS", "http://127.0.0.1:8000/api/interno/resultados")
        self.token = token if token is not None else os.getenv("REACTOR_RESULTADOS_TOKEN", "")
        self._aviso_sin_token = False
        Path(self.archivo).parent.mkdir(parents=True, exist_ok=True)
        with self.conectar() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS resultados_pendientes (
                id_externo TEXT PRIMARY KEY,
                datos TEXT NOT NULL,
                intentos INTEGER NOT NULL DEFAULT 0,
                proximo_intento REAL NOT NULL DEFAULT 0,
                ultimo_error TEXT
            )""")

    def conectar(self):
        db = sqlite3.connect(self.archivo, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def convertir(estado):
        if estado.get("estado") != "FINALIZADA" or not estado.get("resultados_finales"):
            raise ValueError("Solo se pueden guardar partidas finalizadas")
        if not estado.get("fecha_inicio_utc") or not estado.get("fecha_fin_utc"):
            raise ValueError("La partida no tiene fechas de inicio o fin")
        return {
            "id_externo": estado["id_externo"],
            "escenario": "laboratorio",  # La partida aún no registra el mapa seleccionado.
            "inicio_utc": estado["fecha_inicio_utc"],
            "fin_utc": estado["fecha_fin_utc"],
            "duracion_segundos": int(estado["duracion"]),
            "puntuacion_objetivo": int(estado["puntuacion_objetivo"]),
            "motivo_fin": estado["motivo_fin"],
            "resultados_finales": [
                {"id_jugador": j["id_jugador"], "puntos": j["puntos"]}
                for j in estado["resultados_finales"]
            ],
        }

    def agregar(self, estado):
        datos = self.convertir(estado)
        with self.conectar() as db:
            db.execute("INSERT OR IGNORE INTO resultados_pendientes (id_externo, datos) VALUES (?, ?)",
                       (datos["id_externo"], json.dumps(datos, sort_keys=True)))
        return datos["id_externo"]

    def pendientes(self):
        with self.conectar() as db:
            return db.execute("SELECT COUNT(*) FROM resultados_pendientes").fetchone()[0]

    def enviar_pendientes(self, maximo=10):
        """No bloquea el ciclo del juego si se llama mediante asyncio.to_thread()."""
        if not self.token:
            if self.pendientes() and not self._aviso_sin_token:
                LOG.warning("REACTOR_RESULTADOS_TOKEN sin configurar: resultados en cola local")
                self._aviso_sin_token = True
            return 0
        with self.conectar() as db:
            filas = db.execute("""SELECT id_externo, datos, intentos
                FROM resultados_pendientes WHERE proximo_intento <= ?
                ORDER BY rowid LIMIT ?""", (time.time(), maximo)).fetchall()
        enviados = 0
        for id_externo, datos, intentos in filas:
            solicitud = urllib.request.Request(
                self.url, data=datos.encode("utf-8"), method="POST",
                headers={"Content-Type": "application/json", "X-Reactor-Servicio": self.token},
            )
            try:
                with urllib.request.urlopen(solicitud, timeout=4) as respuesta:
                    respuesta.read()
                with self.conectar() as db:
                    db.execute("DELETE FROM resultados_pendientes WHERE id_externo = ?", (id_externo,))
                enviados += 1
                LOG.info("Resultado %s registrado en base de datos", id_externo)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
                intentos += 1
                # Retroceso exponencial para no saturar el servidor.
                espera = min(120, 2 ** min(intentos, 7))
                with self.conectar() as db:
                    db.execute("""UPDATE resultados_pendientes SET
                        intentos = ?, proximo_intento = ?, ultimo_error = ?
                        WHERE id_externo = ?""", (intentos, time.time() + espera, str(error)[:500], id_externo))
                LOG.warning("No se pudo guardar la partida %s: %s", id_externo, error)
        return enviados
