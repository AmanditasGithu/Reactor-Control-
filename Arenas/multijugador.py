"""Multijugador de la arena de la compu.

Cuando el menú abre la arena para una partida multijugador, le pasa estos datos
por variables de entorno:

    REACTOR_PARTIDA_ID   número de partida en el servidor de partidas
    REACTOR_JUGADOR_ID   id de la cuenta del jugador (el mismo del backend)
    REACTOR_NOMBRE_JUGADOR
    REACTOR_ESCENARIO    planta_industrial | laboratorio_subterraneo | complejo_militar
    REACTOR_PARTIDAS_WS  dirección del servidor de partidas, por ejemplo 127.0.0.1:8002

La arena sigue moviendo al jugador, chocando con paredes y guardianes como siempre.
Este módulo le cuenta al servidor dónde está y qué hace, y trae lo que hacen los
demás. Los puntos, el reactor, las terminales, las celdas y el final de la partida
los decide el servidor, para que todos vean lo mismo y el resultado vaya al ranking.

La red trabaja en un hilo aparte: el bucle de dibujo nunca se queda esperando.
"""
import json
import os
import queue
import threading
import time

COLORES_RIVALES = ("NARANJA", "VERDE")
LATIDO_SEGUNDOS = 0.5  # el servidor corta la extracción si pasan 1.5 s sin latido


class SesionMultijugador:
    def __init__(self, id_partida, id_jugador, nombre, escenario, direccion):
        self.id_partida = id_partida
        self.id_jugador = id_jugador
        self.nombre = nombre or "JUGADOR"
        self.escenario = escenario or "planta_industrial"
        self.url = f"ws://{direccion}/ws/partidas/{id_partida}/{id_jugador}"

        self.estado = None          # último estado completo de la partida
        self.conectado = False
        self.error = None
        self.finalizada = False
        self.motivo_fin = None
        self.resultados = []

        self._salida = queue.Queue()
        self._entrada = queue.Queue()
        self._detener = threading.Event()
        self._ultima_posicion = None
        self._extrayendo = False
        self._ultimo_latido = 0.0
        self._celdas_pedidas = set()
        self._hilo = threading.Thread(target=self._trabajar, name="multijugador", daemon=True)
        self._hilo.start()

    @classmethod
    def desde_entorno(cls):
        """Devuelve la sesión si la arena se abrió para multijugador; si no, None (modo solo)."""
        try:
            id_partida = int(os.environ["REACTOR_PARTIDA_ID"])
            id_jugador = int(os.environ["REACTOR_JUGADOR_ID"])
        except (KeyError, ValueError):
            return None
        return cls(
            id_partida, id_jugador,
            os.getenv("REACTOR_NOMBRE_JUGADOR", ""),
            os.getenv("REACTOR_ESCENARIO", "planta_industrial"),
            os.getenv("REACTOR_PARTIDAS_WS", "127.0.0.1:8002"),
        )

    # ---------------- red (hilo aparte) ----------------
    def _trabajar(self):
        try:
            from websockets.sync.client import connect
        except ImportError:
            self.error = "Falta instalar websockets (pip install -r frontend/requirements.txt)"
            return
        try:
            with connect(self.url, open_timeout=5) as conexion:
                self.conectado = True
                while not self._detener.is_set():
                    while True:  # mandar lo pendiente
                        try:
                            conexion.send(json.dumps(self._salida.get_nowait()))
                        except queue.Empty:
                            break
                    try:
                        texto = conexion.recv(timeout=0.03)
                    except TimeoutError:
                        continue
                    try:
                        self._entrada.put(json.loads(texto))
                    except ValueError:
                        pass
        except Exception as error:  # servidor apagado, partida inexistente, se cortó la red
            if not self._detener.is_set():
                self.error = f"Sin conexión con el servidor de partidas: {error}"[:120]
        finally:
            self.conectado = False

    def _enviar(self, datos):
        self._salida.put(datos)

    def cerrar(self):
        if self._extrayendo:
            self._enviar({"tipo": "accion", "senal": "ACCION_SOLTAR"})
        self._detener.set()

    # ---------------- lo que llama la arena ----------------
    def procesar(self):
        """Aplica lo que llegó del servidor. Se llama una vez por cuadro."""
        while True:
            try:
                mensaje = self._entrada.get_nowait()
            except queue.Empty:
                return
            tipo = mensaje.get("tipo")
            if tipo in ("estado", "partida_finalizada"):
                partida = mensaje.get("partida") or {}
                if partida:
                    self.estado = partida
                if tipo == "partida_finalizada" or partida.get("estado") == "FINALIZADA":
                    self.finalizada = True
                    self.motivo_fin = mensaje.get("motivo_fin") or partida.get("motivo_fin") or "TIEMPO"
                    self.resultados = (mensaje.get("resultados_finales")
                                       or partida.get("resultados_finales") or [])

    def configurar_mapa(self, reactor, terminales, celdas, libres):
        """Le pasa al servidor las posiciones del mapa de esta arena (solo vale la primera vez)."""
        self._enviar({
            "tipo": "configurar",
            "reactor": list(reactor),
            "terminales": [list(t) for t in terminales],
            "celdas": [list(c) for c in celdas],
            "bonificaciones": [list(p) for p in libres],
        })

    def actualizar_posicion(self, col, fila):
        if (col, fila) != self._ultima_posicion:
            self._ultima_posicion = (col, fila)
            self._enviar({"tipo": "posicion", "x": int(col), "y": int(fila)})

    def recoger_celda(self, col, fila):
        if (col, fila) not in self._celdas_pedidas:
            self._celdas_pedidas.add((col, fila))
            self._enviar({"tipo": "celda", "x": int(col), "y": int(fila)})

    def extraer(self, quiere, ahora=None):
        """La tecla E o el botón del control físico: igual que el botón del celular."""
        ahora = time.monotonic() if ahora is None else ahora
        if quiere and not self._extrayendo:
            self._extrayendo = True
            self._ultimo_latido = ahora
            self._enviar({"tipo": "accion", "senal": "ACCION_PRESIONAR"})
        elif quiere and ahora - self._ultimo_latido >= LATIDO_SEGUNDOS:
            self._ultimo_latido = ahora
            self._enviar({"tipo": "accion", "senal": "ACCION_LATIDO"})
        elif not quiere and self._extrayendo:
            self._extrayendo = False
            self._enviar({"tipo": "accion", "senal": "ACCION_SOLTAR"})

    # ---------------- datos para dibujar ----------------
    def _jugadores(self):
        return (self.estado or {}).get("jugadores") or []

    def yo(self):
        return next((j for j in self._jugadores() if j.get("id_jugador") == self.id_jugador), None)

    def mis_puntos(self):
        return int((self.yo() or {}).get("puntos", 0))

    def estoy_extrayendo(self):
        return bool((self.yo() or {}).get("extrayendo"))

    def color_de(self, id_jugador):
        if id_jugador == self.id_jugador:
            return "AZUL"
        otros = [j.get("id_jugador") for j in self._jugadores() if j.get("id_jugador") != self.id_jugador]
        indice = otros.index(id_jugador) if id_jugador in otros else 0
        return COLORES_RIVALES[indice % len(COLORES_RIVALES)]

    def rivales(self):
        """Los demás jugadores, en casillas del mapa, con su color para la imagen."""
        return [
            {"id_jugador": j["id_jugador"], "nombre": self.color_de(j["id_jugador"]),
             "nombre_real": j.get("nombre", ""), "x": j["x"], "y": j["y"],
             "puntos": j.get("puntos", 0), "extrayendo": j.get("extrayendo", False)}
            for j in self._jugadores() if j.get("id_jugador") != self.id_jugador
        ]

    def tiempo_restante(self):
        return float((self.estado or {}).get("tiempo_restante", 0) or 0)

    def reactor(self):
        return (self.estado or {}).get("reactor") or {}

    def terminales_activadas(self):
        return {(t["x"], t["y"]) for t in (self.estado or {}).get("terminales") or [] if t.get("activada")}

    def celdas_restantes(self):
        """None si el servidor todavía no mandó las celdas (entonces no se borra ninguna)."""
        celdas = (self.estado or {}).get("celdas")
        return None if celdas is None else {(c[0], c[1]) for c in celdas}

    def resultados_para_victoria(self):
        """Resultados del servidor con el nombre real; el ganador con su color para la imagen."""
        datos = [{"id_jugador": r.get("id_jugador"), "nombre": str(r.get("nombre", "Jugador")),
                  "puntos": int(r.get("puntos", 0))} for r in self.resultados or self._jugadores()]
        datos.sort(key=lambda r: (-r["puntos"], r["id_jugador"] or 0))
        color = self.color_de(datos[0]["id_jugador"]).capitalize() if datos else "Azul"
        return color, datos

    def aviso(self):
        """Texto corto para la pantalla mientras no hay conexión."""
        if self.error:
            return self.error
        if not self.conectado:
            return "Conectando con el servidor de partidas..."
        return None
