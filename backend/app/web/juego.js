// US-024: jugar desde el celular.
// La partida la controla el servidor de partidas (Logica-juego-backend, puerto 8002):
// el celular solo manda lo que toca el jugador (moverse, extraer) y dibuja lo que el servidor responde.
"use strict";

const juego = (() => {
  // El servidor de partidas está en la misma compu que abrió esta página, en el puerto 8002.
  const PUERTO_PARTIDAS = 8002;
  const servidor = `${location.protocol}//${location.hostname}:${PUERTO_PARTIDAS}`;
  const servidorWS = `${location.protocol === "https:" ? "wss" : "ws"}://${location.hostname}:${PUERTO_PARTIDAS}`;

  const COLORES = ["#3c8cff", "#ff9632", "#5adc78", "#e65ad2", "#ffd700", "#00dcc8"];
  const REPETIR_MOVIMIENTO_MS = 160; // al mantener una flecha
  const LATIDO_MS = 500;             // el servidor corta la extracción si pasan 1.5 s sin latido

  let paso = null;          // "sala" | "espera" | "arena" | "fin"
  let idPartida = null;
  let socket = null;
  let estado = null;        // último estado completo que mandó el servidor
  let marcador = null;      // último marcador_actualizado
  let revisarEspera = null; // intervalo mientras se esperan jugadores
  let repetir = null;       // intervalo de la flecha mantenida
  let latido = null;        // intervalo mientras se mantiene EXTRAER
  let limites = null;       // área visible del mapa (solo crece, para que no "salte")

  const yo = () => sesion.actual.jugador;
  const panel = () => $("#pantalla-jugar");

  // ---------- Llamadas al servidor de partidas ----------
  async function partidas(metodo, ruta, datos) {
    const opciones = { method: metodo, headers: {} };
    if (datos !== undefined) {
      opciones.headers["Content-Type"] = "application/json";
      opciones.body = JSON.stringify(datos);
    }
    let respuesta;
    try {
      respuesta = await fetch(servidor + ruta, opciones);
    } catch {
      throw new ErrorAPI("No se pudo conectar con el servidor de partidas (puerto 8002). ¿Está encendido?", 0);
    }
    const cuerpo = await respuesta.json().catch(() => null);
    if (!respuesta.ok) throw new ErrorAPI(mensajeDeError(cuerpo), respuesta.status);
    return cuerpo;
  }

  // ---------- Pasos de la pantalla ----------
  function irA(nuevo, mensaje) {
    paso = nuevo;
    for (const nombre of ["sala", "espera", "arena", "fin"]) $("#juego-" + nombre).hidden = nombre !== nuevo;
    const visible = $("#juego-" + nuevo);
    visible.querySelectorAll(".mensaje").forEach((m) => { m.textContent = ""; m.classList.remove("exito"); });
    if (mensaje) avisar(visible, mensaje);
    window.scrollTo(0, 0);
  }

  function abrir() {
    mostrarSala();
  }

  function cerrar() {
    soltarTodo();
    detenerEspera();
    if (socket) { socket.onclose = null; socket.close(); socket = null; }
    paso = null; idPartida = null; estado = null; marcador = null; limites = null;
  }

  async function mostrarSala(mensaje) {
    cerrar();
    irA("sala", mensaje);
    const lista = $("#partidas-abiertas");
    lista.replaceChildren(elemento("li", "vacio", "Buscando partidas…"));
    try {
      const todas = await partidas("GET", "/partidas");
      const abiertas = todas.filter((p) => p.estado === "ESPERANDO");
      lista.replaceChildren();
      if (!abiertas.length) lista.append(elemento("li", "vacio", "No hay partidas esperando. ¡Creá una!"));
      for (const p of abiertas) {
        const fila = elemento("li", "partida-abierta");
        fila.append(elemento("span", "", `Partida ${p.id_partida} · ${p.cantidad_jugadores} jugador${p.cantidad_jugadores === 1 ? "" : "es"}`));
        const boton = elemento("button", "enlace", "Unirme");
        boton.type = "button";
        boton.addEventListener("click", () => entrar(p.id_partida));
        fila.append(boton);
        lista.append(fila);
      }
    } catch (error) {
      lista.replaceChildren();
      avisar($("#juego-sala"), error.message);
    }
  }

  // Une al jugador (con su id y nombre de la cuenta) y abre la conexión en tiempo real
  async function entrar(numero) {
    try {
      await partidas("POST", `/partidas/${numero}/unirse`, { id_jugador: yo().id, nombre: yo().nombre_usuario });
    } catch (error) {
      // 409 puede ser que ya estaba unido (por ejemplo, si recargó la página): en ese caso se sigue
      const yaEstaba = error.codigo === 409 && await estoyEn(numero);
      if (!yaEstaba) {
        avisar($("#juego-sala"), error.codigo === 409 ? "Esa partida ya empezó o terminó" : error.message);
        return;
      }
    }
    idPartida = numero;
    conectar();
    irA("espera");
    $("#espera-numero").textContent = numero;
    revisarEspera = setInterval(actualizarEspera, 2000);
    actualizarEspera();
  }

  async function estoyEn(numero) {
    try {
      const partida = await partidas("GET", `/partidas/${numero}`);
      return partida.jugadores.some((j) => j.id_jugador === yo().id);
    } catch { return false; }
  }

  // Mientras se espera, se revisa quién entró (el servidor no avisa cuando alguien se une)
  async function actualizarEspera() {
    if (paso !== "espera") return;
    try {
      const partida = await partidas("GET", `/partidas/${idPartida}`);
      dibujarEspera(partida.jugadores);
      if (partida.estado !== "ESPERANDO") empezar();
    } catch (error) {
      avisar($("#juego-espera"), error.message);
    }
  }

  function dibujarEspera(jugadores) {
    const lista = $("#espera-jugadores");
    lista.replaceChildren();
    jugadores.forEach((j, i) => {
      const fila = elemento("li");
      const nombre = elemento("span", "", j.nombre + (j.id_jugador === yo().id ? " (vos)" : ""));
      nombre.style.color = COLORES[i % COLORES.length];
      fila.append(nombre);
      lista.append(fila);
    });
    const faltan = Math.max(0, 2 - jugadores.length);
    $("#iniciar-partida").disabled = faltan > 0;
    $("#iniciar-partida").textContent = faltan ? `Falta ${faltan} jugador para iniciar` : "Iniciar partida";
  }

  function detenerEspera() {
    if (revisarEspera) { clearInterval(revisarEspera); revisarEspera = null; }
  }

  function empezar() {
    if (paso === "arena" || paso === "fin") return;
    detenerEspera();
    irA("arena");
    dibujar();
  }

  // ---------- Conexión en tiempo real ----------
  function conectar() {
    socket = new WebSocket(`${servidorWS}/ws/partidas/${idPartida}/${yo().id}`);
    socket.onmessage = (e) => {
      let mensaje;
      try { mensaje = JSON.parse(e.data); } catch { return; }
      recibir(mensaje);
    };
    socket.onclose = () => {
      socket = null;
      soltarTodo();
      if (paso === "espera" || paso === "arena") {
        mostrarSala("Se perdió la conexión con la partida. Si tu sesión está abierta en otro lado, cerrala y volvé a unirte.");
      }
    };
  }

  function enviar(datos) {
    if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(datos));
  }

  function recibir(mensaje) {
    switch (mensaje.tipo) {
      case "estado":
        estado = mensaje.partida;
        if (paso === "espera") dibujarEspera(estado.jugadores);
        if (estado.estado === "JUGANDO") empezar();
        if (estado.estado === "FINALIZADA") terminar(estado);
        dibujar();
        break;
      case "marcador_actualizado":
        marcador = mensaje;
        dibujarMarcador();
        break;
      case "terminal_activada":
        if (mensaje.id_jugador === yo().id) avisoJuego(`¡Terminal activada! +${mensaje.puntos_obtenidos} puntos`);
        break;
      case "bonificacion_recogida":
        avisoJuego(mensaje.id_jugador === yo().id ? "¡Puntos dobles por unos segundos!" : "Otro jugador tomó la bonificación");
        break;
      case "aviso":
        avisoJuego(mensaje.mensaje);
        break;
      case "partida_finalizada":
        terminar(mensaje.partida || mensaje);
        break;
      default:
        break; // jugador_conectado, errores de movimiento, etc.: no hace falta mostrarlos
    }
  }

  let ocultarAviso = null;
  function avisoJuego(texto) {
    const aviso = $("#aviso-juego");
    aviso.textContent = texto;
    clearTimeout(ocultarAviso);
    ocultarAviso = setTimeout(() => { aviso.textContent = ""; }, 2500);
  }

  function terminar(final) {
    if (paso === "fin") return;
    soltarTodo();
    irA("fin");
    const motivos = { TIEMPO: "Se acabó el tiempo", PUNTUACION: "Alguien llegó a la meta" };
    $("#fin-motivo").textContent = motivos[final.motivo_fin] || "La partida terminó";
    const lista = $("#fin-resultados");
    lista.replaceChildren();
    (final.resultados_finales || []).forEach((r, i) => {
      const fila = elemento("li", r.id_jugador === yo().id ? "yo" : "");
      fila.append(elemento("span", "posicion", String(i + 1)));
      fila.append(elemento("span", "nombre", r.nombre || `Jugador ${r.id_jugador}`));
      fila.append(elemento("span", "puntos", String(r.puntos)));
      lista.append(fila);
    });
    if (socket) { socket.onclose = null; socket.close(); socket = null; }
  }

  // ---------- Controles ----------
  function mover(direccion) { enviar({ tipo: "mover", direccion }); }

  function soltarTodo() {
    if (repetir) { clearInterval(repetir); repetir = null; }
    if (latido) {
      clearInterval(latido); latido = null;
      enviar({ tipo: "accion", senal: "ACCION_SOLTAR" });
    }
    $("#extraer").classList.remove("activo");
  }

  function prepararControles() {
    // Flechas: un toque mueve una casilla; mantener sigue moviendo
    document.querySelectorAll("[data-direccion]").forEach((boton) => {
      boton.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        if (repetir) clearInterval(repetir);
        mover(boton.dataset.direccion);
        repetir = setInterval(() => mover(boton.dataset.direccion), REPETIR_MOVIMIENTO_MS);
      });
      for (const fin of ["pointerup", "pointerleave", "pointercancel"]) {
        boton.addEventListener(fin, () => { if (repetir) { clearInterval(repetir); repetir = null; } });
      }
      boton.addEventListener("contextmenu", (e) => e.preventDefault());
    });

    // EXTRAER funciona como el botón del control físico: se mantiene presionado cerca del reactor
    const extraer = $("#extraer");
    extraer.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      if (latido) return;
      extraer.classList.add("activo");
      enviar({ tipo: "accion", senal: "ACCION_PRESIONAR" });
      latido = setInterval(() => enviar({ tipo: "accion", senal: "ACCION_LATIDO" }), LATIDO_MS);
    });
    for (const fin of ["pointerup", "pointerleave", "pointercancel"]) {
      extraer.addEventListener(fin, () => {
        if (!latido) return;
        clearInterval(latido); latido = null;
        extraer.classList.remove("activo");
        enviar({ tipo: "accion", senal: "ACCION_SOLTAR" });
      });
    }
    extraer.addEventListener("contextmenu", (e) => e.preventDefault());

    // En la compu también se puede jugar con las flechas del teclado
    const teclas = { ArrowUp: "ARRIBA", ArrowDown: "ABAJO", ArrowLeft: "IZQUIERDA", ArrowRight: "DERECHA" };
    document.addEventListener("keydown", (e) => {
      if (paso !== "arena" || !teclas[e.key]) return;
      e.preventDefault();
      mover(teclas[e.key]);
    });

    $("#crear-partida").addEventListener("click", async (e) => {
      e.target.disabled = true;
      try {
        const nueva = await partidas("POST", "/partidas");
        await entrar(nueva.id_partida);
      } catch (error) {
        avisar($("#juego-sala"), error.message);
      } finally {
        e.target.disabled = false;
      }
    });

    $("#form-unirse").addEventListener("submit", (e) => {
      e.preventDefault();
      const numero = Number(datosDe(e.target).id_partida);
      if (!Number.isInteger(numero) || numero <= 0) {
        avisar($("#juego-sala"), "Escribí el número de la partida");
        return;
      }
      entrar(numero);
    });

    $("#iniciar-partida").addEventListener("click", async (e) => {
      e.target.disabled = true;
      try {
        await partidas("POST", `/partidas/${idPartida}/iniciar`);
        empezar();
      } catch (error) {
        avisar($("#juego-espera"), error.codigo === 409 ? "Se necesitan al menos 2 jugadores" : error.message);
        e.target.disabled = false;
      }
    });

    $("#salir-espera").addEventListener("click", () => mostrarSala());
    $("#jugar-otra").addEventListener("click", () => mostrarSala());
    window.addEventListener("resize", dibujar);
  }

  // ---------- Dibujo de la arena ----------
  function colorDe(idJugador) {
    const i = estado ? estado.jugadores.findIndex((j) => j.id_jugador === idJugador) : 0;
    return COLORES[Math.max(0, i) % COLORES.length];
  }

  // El mapa no tiene paredes: se muestra de 0 a 10 y se agranda si alguien sale de ahí
  function calcularLimites() {
    const puntos = [
      ...estado.jugadores, ...estado.terminales, estado.reactor,
      ...(estado.bonificacion_disponible ? [estado.bonificacion_disponible] : []),
    ];
    const xs = puntos.map((p) => p.x), ys = puntos.map((p) => p.y);
    const nuevo = {
      minX: Math.min(0, ...xs), maxX: Math.max(10, ...xs),
      minY: Math.min(0, ...ys), maxY: Math.max(10, ...ys),
    };
    if (!limites) limites = nuevo;
    limites = {
      minX: Math.min(limites.minX, nuevo.minX), maxX: Math.max(limites.maxX, nuevo.maxX),
      minY: Math.min(limites.minY, nuevo.minY), maxY: Math.max(limites.maxY, nuevo.maxY),
    };
    return limites;
  }

  function dibujar() {
    if (paso !== "arena" || !estado) return;
    const lienzo = $("#arena");
    const l = calcularLimites();
    const columnas = l.maxX - l.minX + 1, filas = l.maxY - l.minY + 1;
    const ancho = lienzo.parentElement.clientWidth;
    const lado = Math.floor(ancho / columnas);
    const escala = window.devicePixelRatio || 1;
    lienzo.style.width = lado * columnas + "px";
    lienzo.style.height = lado * filas + "px";
    lienzo.width = lado * columnas * escala;
    lienzo.height = lado * filas * escala;
    const g = lienzo.getContext("2d");
    g.scale(escala, escala);
    g.textAlign = "center";
    g.textBaseline = "middle";
    const px = (x) => (x - l.minX) * lado, py = (y) => (y - l.minY) * lado;
    const centro = (v, f) => f(v) + lado / 2;

    // Piso
    g.fillStyle = "#1c2230";
    g.fillRect(0, 0, lado * columnas, lado * filas);
    g.strokeStyle = "#2a3142";
    g.lineWidth = 1;
    for (let c = 0; c <= columnas; c++) { g.beginPath(); g.moveTo(c * lado + 0.5, 0); g.lineTo(c * lado + 0.5, lado * filas); g.stroke(); }
    for (let f = 0; f <= filas; f++) { g.beginPath(); g.moveTo(0, f * lado + 0.5); g.lineTo(lado * columnas, f * lado + 0.5); g.stroke(); }

    // Zona del reactor: las casillas desde donde se puede extraer
    const r = estado.reactor;
    g.fillStyle = r.recargando ? "rgba(150,155,170,0.18)" : "rgba(255,215,0,0.14)";
    for (let x = r.x - r.radio; x <= r.x + r.radio; x++) {
      for (let y = r.y - r.radio; y <= r.y + r.radio; y++) {
        if (Math.hypot(x - r.x, y - r.y) <= r.radio) g.fillRect(px(x) + 1, py(y) + 1, lado - 1, lado - 1);
      }
    }
    // Reactor (con su energía)
    const carga = r.energia_maxima ? r.energia_actual / r.energia_maxima : 0;
    g.beginPath();
    g.arc(centro(r.x, px), centro(r.y, py), lado * 0.42, 0, Math.PI * 2);
    g.fillStyle = r.recargando ? "#969baa" : "#ffd700";
    g.fill();
    g.beginPath();
    g.arc(centro(r.x, px), centro(r.y, py), lado * 0.42, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * carga);
    g.strokeStyle = "#00dcc8";
    g.lineWidth = Math.max(2, lado * 0.08);
    g.stroke();

    // Terminales
    for (const t of estado.terminales) {
      g.fillStyle = t.activada ? "#323848" : "#00dcc8";
      g.fillRect(px(t.x) + lado * 0.2, py(t.y) + lado * 0.2, lado * 0.6, lado * 0.6);
      g.fillStyle = t.activada ? "#969baa" : "#141923";
      g.font = `bold ${Math.floor(lado * 0.32)}px system-ui, sans-serif`;
      g.fillText(t.activada ? "✓" : "T", centro(t.x, px), centro(t.y, py));
    }

    // Bonificación (puntos dobles)
    const b = estado.bonificacion_disponible;
    if (b) {
      g.fillStyle = "#e65ad2";
      estrella(g, centro(b.x, px), centro(b.y, py), lado * 0.4, lado * 0.18);
      g.fillStyle = "#ffffff";
      g.font = `bold ${Math.floor(lado * 0.26)}px system-ui, sans-serif`;
      g.fillText("x2", centro(b.x, px), centro(b.y, py) + 1);
    }

    // Jugadores (el propio con borde blanco, encima de todos)
    const ordenados = [...estado.jugadores].sort((a, c) => (a.id_jugador === yo().id) - (c.id_jugador === yo().id));
    for (const j of ordenados) {
      const esYo = j.id_jugador === yo().id;
      g.beginPath();
      g.arc(centro(j.x, px), centro(j.y, py), lado * 0.34, 0, Math.PI * 2);
      g.fillStyle = colorDe(j.id_jugador);
      g.fill();
      if (esYo || j.extrayendo || j.bonificacion) {
        g.lineWidth = Math.max(2, lado * 0.08);
        g.strokeStyle = j.extrayendo ? "#ffd700" : j.bonificacion ? "#e65ad2" : "#ffffff";
        g.stroke();
      }
      g.fillStyle = "#141923";
      g.font = `bold ${Math.floor(lado * 0.3)}px system-ui, sans-serif`;
      g.fillText((j.nombre || "?").charAt(0).toUpperCase(), centro(j.x, px), centro(j.y, py) + 1);
    }

    // Datos de arriba
    $("#hud-tiempo").textContent = formatoTiempo(estado.tiempo_restante);
    $("#hud-meta").textContent = estado.puntuacion_objetivo;
    $("#hud-reactor").textContent = r.recargando ? "recargando" : `${r.energia_actual}/${r.energia_maxima}`;
    const propio = estado.jugadores.find((j) => j.id_jugador === yo().id);
    $("#extraer").classList.toggle("activo", Boolean(propio && propio.extrayendo) || Boolean(latido));
    if (!marcador) dibujarMarcador();
  }

  function estrella(g, cx, cy, externo, interno) {
    g.beginPath();
    for (let i = 0; i < 10; i++) {
      const radio = i % 2 ? interno : externo;
      const angulo = -Math.PI / 2 + (i * Math.PI) / 5;
      g.lineTo(cx + Math.cos(angulo) * radio, cy + Math.sin(angulo) * radio);
    }
    g.closePath();
    g.fill();
  }

  function formatoTiempo(segundos) {
    const s = Math.max(0, Math.ceil(Number(segundos) || 0));
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  // Marcador: lo que manda el servidor (US-017); si todavía no llegó, se arma con el estado
  function dibujarMarcador() {
    if (paso !== "arena") return;
    const jugadores = marcador ? marcador.jugadores
      : estado ? [...estado.jugadores].sort((a, b) => b.puntos - a.puntos) : [];
    const lista = $("#marcador");
    lista.replaceChildren();
    jugadores.forEach((j, i) => {
      const fila = elemento("li", j.id_jugador === yo().id ? "yo" : "");
      const posicion = elemento("span", "posicion", String(i + 1));
      posicion.style.color = colorDe(j.id_jugador);
      fila.append(posicion);
      const nombre = elemento("span", "nombre", j.nombre);
      if (j.bonificacion) nombre.append(elemento("small", "", "puntos dobles"));
      else if (j.extrayendo) nombre.append(elemento("small", "", "extrayendo energía"));
      fila.append(nombre);
      fila.append(elemento("span", "puntos", String(j.puntos)));
      lista.append(fila);
    });
  }

  prepararControles();
  return { abrir, cerrar };
})();
