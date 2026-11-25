"""US-017: cliente de SOLO LECTURA del marcador del servidor de partidas.

La red trabaja en un hilo, nunca dentro del bucle de dibujo de Pygame.
Los eventos se procesan en el hilo principal. Este módulo no otorga puntos.
"""

from copy import deepcopy
import json
import queue
import threading


class EstadoMarcador:
    """Estado visible con protección frente a revisiones desordenadas."""

    def __init__(self):
        self.conexion = "SIN CONFIGURAR"
        self.revision = -1
        self.estado = None
        self.jugadores = []
        self.reactor = None
        self.bonificacion_disponible = None
        self.meta = None
        self.tiempo_restante = None
        self.resultados_finales = []
        self.motivo_fin = None
        self.id_partida = None

    @property
    def finalizada(self):
        return self.estado == "FINALIZADA"

    def aplicar(self, mensaje):
        """Devuelve True si cambió información significativa del marcador."""
        if not isinstance(mensaje, dict):
            return False
        tipo = mensaje.get("tipo")
        if tipo == "conexion":
            self.conexion = "CONECTADO"
            # Un servidor reiniciado puede volver a comenzar desde revision 1.
            self.revision = -1
            self.jugadores = []
            self.reactor = None
            self.bonificacion_disponible = None
            self.estado = None
            self.resultados_finales = []
            return True
        if tipo == "desconexion":
            self.conexion = "DESCONECTADO"
            return True
        if tipo == "marcador_actualizado":
            revision = mensaje.get("revision")
            if not isinstance(revision, int) or isinstance(revision, bool):
                return False
            if revision <= self.revision:
                return False
            self.revision = revision
            self.id_partida = mensaje.get("id_partida", self.id_partida)
            self.estado = mensaje.get("estado", self.estado)
            self.meta = mensaje.get("puntuacion_objetivo", self.meta)
            self.motivo_fin = mensaje.get("motivo_fin", self.motivo_fin)
            self.jugadores = deepcopy(mensaje.get("jugadores") or [])
            self.reactor = deepcopy(mensaje.get("reactor"))
            self.bonificacion_disponible = deepcopy(mensaje.get("bonificacion_disponible"))
            return True
        if tipo in ("estado", "partida_finalizada"):
            partida = mensaje.get("partida") or {}
            if not isinstance(partida, dict):
                return False
            if "tiempo_restante" in partida:
                self.tiempo_restante = partida["tiempo_restante"]
            if self.revision == -1:
                self.id_partida = partida.get("id_partida", self.id_partida)
                self.jugadores = deepcopy(partida.get("jugadores") or [])
                self.reactor = deepcopy(partida.get("reactor"))
                self.bonificacion_disponible = deepcopy(partida.get("bonificacion_disponible"))
                self.meta = partida.get("puntuacion_objetivo", self.meta)
                self.estado = partida.get("estado", self.estado)
            if tipo == "partida_finalizada":
                self.estado = "FINALIZADA"
                self.motivo_fin = mensaje.get("motivo_fin") or partida.get("motivo_fin")
                self.resultados_finales = deepcopy(
                    mensaje.get("resultados_finales") or partida.get("resultados_finales") or []
                )
                # El evento final de servidor es autoritativo incluso sin nuevo marcador.
                self.jugadores = deepcopy(partida.get("jugadores") or self.jugadores)
                self.reactor = deepcopy(partida.get("reactor") or self.reactor)
                self.bonificacion_disponible = deepcopy(partida.get("bonificacion_disponible"))
            return True
        return False

    def datos_para_victoria(self):
        """No fabrica un podio: usa exclusivamente el resultado del servidor."""
        if not self.finalizada:
            return [], None
        participantes = self.resultados_finales or self.jugadores
        if not participantes:
            return [], None
        datos = [
            {"nombre": str(j.get("nombre", "Jugador")),
             "puntos": int(j.get("puntos", 0))}
            for j in participantes
        ]
        datos.sort(key=lambda j: -j["puntos"])
        ganador = datos[0]["nombre"] if (len(datos) == 1 or datos[0]["puntos"] > datos[1]["puntos"]) else None
        return datos, ganador

    def copiar(self):
        return deepcopy({
            "conexion": self.conexion,
            "revision": self.revision,
            "id_partida": self.id_partida,
            "estado": self.estado,
            "jugadores": self.jugadores,
            "reactor": self.reactor,
            "bonificacion_disponible": self.bonificacion_disponible,
            "meta": self.meta,
            "tiempo_restante": self.tiempo_restante,
            "motivo_fin": self.motivo_fin,
        })


class ClienteMarcadorArena:
    """Escucha `marcador_actualizado`, `estado` y `partida_finalizada`."""

    def __init__(self, url):
        self.url = url
        self._eventos = queue.Queue(maxsize=512)
        self._detener = threading.Event()
        self._socket = None
        self._hilo = threading.Thread(target=self._escuchar, name="US017-marcador", daemon=True)
        self._hilo.start()

    def _publicar(self, evento):
        try:
            self._eventos.put_nowait(evento)
        except queue.Full:
            # Ante una sobrecarga, el siguiente estado completo recupera la vista.
            try:
                self._eventos.get_nowait()
            except queue.Empty:
                pass
            try:
                self._eventos.put_nowait(evento)
            except queue.Full:
                pass

    def _escuchar(self):
        try:
            from websockets.sync.client import connect
        except ImportError:
            self._publicar({"tipo": "desconexion", "mensaje": "Instalar websockets>=14"})
            return
        while not self._detener.is_set():
            try:
                with connect(self.url, open_timeout=3, close_timeout=2) as ws:
                    self._socket = ws
                    self._publicar({"tipo": "conexion"})
                    for texto in ws:
                        if self._detener.is_set():
                            break
                        try:
                            mensaje = json.loads(texto)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(mensaje, dict):
                            self._publicar(mensaje)
            except (Exception,) as error:
                if not self._detener.is_set():
                    self._publicar({"tipo": "desconexion", "mensaje": str(error)[:120]})
            finally:
                self._socket = None
            if not self._detener.is_set():
                self._publicar({"tipo": "desconexion"})
                self._detener.wait(2.0)

    def procesar_pendientes(self, estado):
        """Llamar desde el hilo de Pygame una vez por frame."""
        cantidad = 0
        while cantidad < 512:
            try:
                mensaje = self._eventos.get_nowait()
            except queue.Empty:
                break
            estado.aplicar(mensaje)
            cantidad += 1
        return cantidad

    def cerrar(self):
        self._detener.set()
        socket = self._socket
        if socket is not None:
            try:
                socket.close()
            except Exception:
                pass
        if self._hilo.is_alive():
            self._hilo.join(timeout=2.0)
