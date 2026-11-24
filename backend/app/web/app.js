// Versión para celular (US-024). Usa las mismas rutas del backend que el juego en Pygame.
"use strict";

const MENSAJES_CAMPOS = {
  nombre_usuario: "El usuario debe tener de 3 a 30 caracteres: letras, números o _",
  correo: "Escribí un correo válido (ejemplo: ana@correo.com)",
  contrasena: "La contraseña debe tener al menos 8 caracteres",
  usuario_o_correo: "Escribí tu usuario o correo",
  codigo: "El código son 6 números",
  contrasena_nueva: "La contraseña nueva debe tener al menos 8 caracteres",
};

// ---------- Sesión (el token se guarda en este navegador) ----------
const sesion = {
  leer() {
    try { return JSON.parse(localStorage.getItem("reactor_sesion")); } catch { return null; }
  },
  guardar(token, jugador) {
    try { localStorage.setItem("reactor_sesion", JSON.stringify({ token, jugador })); } catch { /* sin almacenamiento */ }
    sesion.actual = { token, jugador };
  },
  borrar() {
    try { localStorage.removeItem("reactor_sesion"); } catch { /* sin almacenamiento */ }
    sesion.actual = null;
  },
  actual: null,
};

// ---------- Conexión con el backend ----------
class ErrorAPI extends Error {
  constructor(mensaje, codigo) { super(mensaje); this.codigo = codigo; }
}

async function api(metodo, ruta, datos) {
  const opciones = { method: metodo, headers: {} };
  if (datos !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(datos);
  }
  if (sesion.actual) opciones.headers.Authorization = "Bearer " + sesion.actual.token;

  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch {
    throw new ErrorAPI("No se pudo conectar con el servidor. Revisá tu conexión.", 0);
  }
  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) throw new ErrorAPI(mensajeDeError(cuerpo), respuesta.status);
  return cuerpo;
}

function mensajeDeError(cuerpo) {
  const detalle = cuerpo && cuerpo.detail;
  if (typeof detalle === "string") return detalle;
  if (Array.isArray(detalle) && detalle.length) {
    const campo = detalle[0].loc ? detalle[0].loc[detalle[0].loc.length - 1] : "";
    return MENSAJES_CAMPOS[campo] || "Revisá los datos ingresados";
  }
  return "Ocurrió un error en el servidor";
}

// ---------- Pantallas ----------
const $ = (selector, dentro = document) => dentro.querySelector(selector);

function mostrar(nombre, mensaje, exito = false) {
  document.querySelectorAll(".pantalla").forEach((p) => { p.hidden = true; });
  const pantalla = $("#pantalla-" + nombre);
  pantalla.hidden = false;
  pantalla.querySelectorAll(".mensaje").forEach((m) => { m.textContent = ""; m.classList.remove("exito"); });
  if (mensaje) avisar(pantalla, mensaje, exito);
  window.scrollTo(0, 0);
  if (nombre === "menu") $("#nombre-jugador").textContent = sesion.actual.jugador.nombre_usuario;
  if (nombre === "perfil") cargarPerfil();
  if (nombre === "ranking") cargarRanking();
  if (nombre === "recuperar") {
    $("#form-pedir-codigo").hidden = false;
    $("#form-nueva-contrasena").hidden = true;
  }
}

// Muestra un mensaje en el primer cuadro de mensaje visible dentro de `lugar` (un formulario o una pantalla)
function avisar(lugar, texto, exito = false) {
  const mensaje = [...lugar.querySelectorAll(".mensaje")].find((m) => !m.closest("[hidden]"));
  if (!mensaje) return;
  mensaje.textContent = texto;
  mensaje.classList.toggle("exito", exito);
}

function datosDe(form) {
  return Object.fromEntries([...new FormData(form)].map(([k, v]) => [k, String(v).trim()]));
}

// Desactiva el botón mientras se espera al servidor, para no enviar dos veces
async function conEspera(form, accion) {
  const boton = $("button[type=submit]", form);
  boton.disabled = true;
  try {
    await accion();
  } catch (error) {
    avisar(form, error instanceof ErrorAPI ? error.message : "Ocurrió un error inesperado");
  } finally {
    boton.disabled = false;
  }
}

function iniciarSesion(token, jugador) {
  sesion.guardar(token, jugador);
  mostrar("menu");
}

// ---------- US-004: login ----------
$("#form-login").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const datos = datosDe(form);
  datos.contrasena = form.contrasena.value; // la contraseña no se recorta
  if (!datos.usuario_o_correo || !datos.contrasena) return avisar(form, "Completá todos los campos");
  conEspera(form, async () => {
    try {
      const r = await api("POST", "/api/auth/login", datos);
      iniciarSesion(r.access_token, r.jugador);
    } catch (error) {
      if (error.codigo === 403) { // US-003: falta verificar el correo
        mostrar("verificar", "Verificá tu correo antes de iniciar sesión");
        $("#form-verificar").correo.value = datos.usuario_o_correo.includes("@") ? datos.usuario_o_correo : "";
        return;
      }
      form.contrasena.value = "";
      throw error;
    }
  });
});

// ---------- US-001: registro ----------
$("#form-registro").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const datos = datosDe(form);
  if (Object.values(datos).some((v) => !v)) return avisar(form, "Completá todos los campos");
  if (form.contrasena.value !== form.confirmar.value) return avisar(form, "Las contraseñas no coinciden");
  conEspera(form, async () => {
    const jugador = await api("POST", "/api/auth/registro", {
      nombre_usuario: datos.nombre_usuario, correo: datos.correo, contrasena: form.contrasena.value,
    });
    form.reset();
    mostrar("verificar", "¡Cuenta creada! Te enviamos un código a tu correo", true);
    $("#form-verificar").correo.value = jugador.correo;
    $("#form-verificar").codigo.focus();
  });
});

// ---------- US-003: verificar correo ----------
$("#form-verificar").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const datos = datosDe(form);
  if (!datos.correo || !datos.codigo) return avisar(form, "Completá todos los campos");
  conEspera(form, async () => {
    await api("POST", "/api/auth/verificar", datos);
    form.reset();
    mostrar("login", "¡Correo verificado! Ahora iniciá sesión", true);
    $("#form-login").usuario_o_correo.value = datos.correo;
  });
});

$("#reenviar-codigo").addEventListener("click", async () => {
  const form = $("#form-verificar");
  const correo = form.correo.value.trim();
  if (!correo) return avisar(form, "Escribí tu correo");
  try {
    await api("POST", "/api/auth/verificar/reenviar", { correo });
    form.codigo.value = "";
    avisar(form, "Te enviamos un código nuevo", true);
  } catch (error) {
    avisar(form, error.message);
  }
});

// ---------- US-005: recuperar contraseña ----------
let correoRecuperacion = "";

$("#form-pedir-codigo").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const { correo } = datosDe(form);
  if (!correo) return avisar(form, "Escribí tu correo");
  conEspera(form, async () => {
    await api("POST", "/api/auth/recuperar/solicitar", { correo });
    correoRecuperacion = correo;
    form.hidden = true;
    const siguiente = $("#form-nueva-contrasena");
    siguiente.hidden = false;
    avisar(siguiente, "Si el correo está registrado, te llegó un código", true);
  });
});

$("#form-nueva-contrasena").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  if (!form.codigo.value.trim() || !form.contrasena_nueva.value || !form.confirmar.value) {
    return avisar(form, "Completá todos los campos");
  }
  if (form.contrasena_nueva.value !== form.confirmar.value) return avisar(form, "Las contraseñas no coinciden");
  conEspera(form, async () => {
    await api("POST", "/api/auth/recuperar/restablecer", {
      correo: correoRecuperacion, codigo: form.codigo.value.trim(), contrasena_nueva: form.contrasena_nueva.value,
    });
    form.reset();
    $("#form-pedir-codigo").reset();
    mostrar("login", "Contraseña cambiada. Iniciá sesión", true);
    $("#form-login").usuario_o_correo.value = correoRecuperacion;
  });
});

// ---------- US-002: Google y GitHub ----------
document.querySelectorAll("[data-proveedor]").forEach((boton) => {
  boton.addEventListener("click", async () => {
    const pantalla = $("#pantalla-login");
    // La pestaña se abre en el mismo toque, si no el celular la bloquea como ventana emergente
    const pestana = window.open("", "_blank");
    try {
      const inicio = await api("POST", `/api/auth/social/${boton.dataset.proveedor}/iniciar`);
      if (pestana) pestana.location = inicio.url; else window.open(inicio.url, "_blank");
      avisar(pantalla, "Completá el inicio de sesión en la pestaña nueva y volvé aquí", true);
      esperarRedSocial(inicio.codigo_espera, pantalla);
    } catch (error) {
      if (pestana) pestana.close();
      avisar(pantalla, error.message);
    }
  });
});

function esperarRedSocial(codigoEspera, pantalla) {
  const limite = Date.now() + 10 * 60 * 1000; // el inicio vence a los 10 minutos
  const revisar = async () => {
    try {
      const r = await api("POST", "/api/auth/social/revisar", { codigo_espera: codigoEspera });
      if (r.estado === "listo") return iniciarSesion(r.access_token, r.jugador);
      if (r.estado === "error") return avisar(pantalla, r.mensaje || "No se pudo iniciar sesión");
    } catch (error) {
      return avisar(pantalla, error.message);
    }
    if (Date.now() < limite && !$("#pantalla-login").hidden) setTimeout(revisar, 2000);
  };
  setTimeout(revisar, 2000);
}

// ---------- US-006: perfil ----------
function fecha(texto) {
  return texto ? new Date(texto).toLocaleDateString("es-CR", { day: "numeric", month: "short", year: "numeric" }) : "";
}

function elemento(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

function filaLista(lista, izquierda, derecha) {
  const li = elemento("li");
  li.append(elemento("span", "", izquierda), elemento("span", "", derecha));
  lista.append(li);
}

async function cargarPerfil() {
  const datos = $("#perfil-datos");
  datos.textContent = "Cargando…";
  try {
    const p = await api("GET", "/api/perfil");
    datos.replaceChildren(
      elemento("p", "", p.nombre_usuario),
      elemento("p", "dato", p.correo),
      elemento("p", "dato", "Jugador desde " + fecha(p.fecha_registro)),
    );
    const estadisticas = $("#perfil-estadisticas");
    estadisticas.replaceChildren();
    [["Puntos", p.puntos_totales], ["Posición", "#" + p.posicion_ranking],
     ["Victorias", p.victorias], ["Partidas", p.partidas_jugadas]].forEach(([nombre, valor]) => {
      const caja = elemento("div", "estadistica");
      caja.append(elemento("b", "", String(valor)), elemento("span", "", nombre));
      estadisticas.append(caja);
    });

    const historial = $("#perfil-historial");
    historial.replaceChildren();
    p.historial.forEach((h) => filaLista(historial,
      `${fecha(h.fecha)} · ${h.escenario}`, `${h.puntos} pts${h.posicion ? " · " + h.posicion + "º" : ""}`));
    if (!p.historial.length) historial.append(elemento("li", "vacio", "Todavía no jugaste partidas"));

    const records = $("#perfil-records");
    records.replaceChildren();
    p.records.forEach((r) => filaLista(records, r.tipo.replaceAll("_", " "), String(r.valor)));
    if (!p.records.length) records.append(elemento("li", "vacio", "Todavía no tenés récords"));
  } catch (error) {
    if (error.codigo === 401) return cerrarSesion("Tu sesión venció. Iniciá sesión de nuevo.");
    datos.textContent = error.message;
  }
}

// ---------- US-022: ranking ----------
async function cargarRanking() {
  const lista = $("#ranking-lista");
  lista.replaceChildren(elemento("li", "", "Cargando…"));
  try {
    const filas = await api("GET", "/api/ranking?limite=10");
    lista.replaceChildren();
    filas.forEach((f) => {
      const li = elemento("li", sesion.actual && f.nombre_usuario === sesion.actual.jugador.nombre_usuario ? "yo" : "");
      const nombre = elemento("span", "nombre", f.nombre_usuario);
      nombre.append(elemento("small", "", `${f.victorias} victorias · ${f.partidas_jugadas} partidas`));
      li.append(elemento("span", "posicion", String(f.posicion)), nombre, elemento("span", "puntos", f.puntos_totales + " pts"));
      lista.append(li);
    });
    if (!filas.length) lista.append(elemento("li", "", "Todavía no hay jugadores en el ranking"));
  } catch (error) {
    lista.replaceChildren(elemento("li", "", error.message));
  }
}

// ---------- Navegación ----------
function cerrarSesion(mensaje, exito = false) {
  sesion.borrar();
  mostrar("login", mensaje || "", exito);
}

document.addEventListener("click", (e) => {
  const destino = e.target.closest("[data-ir]");
  if (destino) mostrar(destino.dataset.ir);
});
$("#cerrar-sesion").addEventListener("click", () => cerrarSesion("Sesión cerrada", true));

// Al abrir la página: si ya había una sesión válida en este celular, se entra directo al menú
(async () => {
  const guardada = sesion.leer();
  if (!guardada) return mostrar("login");
  sesion.actual = guardada;
  try {
    const jugador = await api("GET", "/api/auth/yo");
    sesion.guardar(guardada.token, jugador);
    mostrar("menu");
  } catch {
    sesion.borrar();
    mostrar("login");
  }
})();
