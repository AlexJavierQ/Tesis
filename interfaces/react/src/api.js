// Cliente HTTP de la API. Todo el frontend habla con el backend por aqui.
// Si cambia la API, solo se toca este archivo.

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// El token se guarda en localStorage para que la sesion sobreviva a un F5.
const TOKEN = "asistente_token";

export function getToken() {
  return localStorage.getItem(TOKEN);
}
export function setToken(t) {
  localStorage.setItem(TOKEN, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN);
}

// Envuelve fetch: agrega el header Authorization automaticamente si hay token,
// y convierte los errores HTTP en Excepciones con un mensaje legible.
async function pedir(ruta, opciones = {}) {
  const token = getToken();
  const headers = { ...(opciones.headers || {}) };
  if (token) headers["Authorization"] = "Bearer " + token;

  const r = await fetch(BASE + ruta, { ...opciones, headers });
  if (!r.ok) {
    let mensaje = "Error " + r.status;
    try {
      const cuerpo = await r.json();
      if (cuerpo.detail) mensaje = cuerpo.detail;
    } catch {
      /* respuesta sin JSON: nos quedamos con el codigo */
    }
    throw new Error(mensaje);
  }
  return r.json();
}

export const api = {
  // sesion
  login: (usuario, password) =>
    pedir("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, password }),
    }),
  me: () => pedir("/me"),
  logout: () => pedir("/logout", { method: "POST" }),

  // estructura
  salud: () => pedir("/salud"),
  facultades: () => pedir("/facultades"),
  carreras: () => pedir("/carreras"),
  cursos: (carrera) => pedir(`/carreras/${encodeURIComponent(carrera)}/cursos`),

  crearCurso: (carrera, nombre) => {
    const fd = new FormData();
    fd.append("nombre", nombre);
    return pedir(`/carreras/${encodeURIComponent(carrera)}/cursos`, {
      method: "POST",
      body: fd,
    });
  },

  // consulta. modo: "general" | "curso" | "ambos" (desde donde se responde)
  preguntar: (pregunta, carrera, curso, modo, conversacionId) =>
    pedir("/preguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pregunta, carrera, curso: curso || null, modo,
        conversacion_id: conversacionId || null,
      }),
    }),

  // ---------- historial de chat ----------
  conversaciones: {
    listar: () => pedir("/conversaciones"),
    crear: (titulo) => {
      const fd = new FormData();
      fd.append("titulo", titulo || "");
      return pedir("/conversaciones", { method: "POST", body: fd });
    },
    ver: (id) => pedir(`/conversaciones/${id}`),
    borrar: (id) => pedir(`/conversaciones/${id}`, { method: "DELETE" }),
  },

  // documentos
  documentos: (carrera, curso) => {
    const q = new URLSearchParams({ carrera });
    if (curso) q.append("curso", curso);
    return pedir("/documentos?" + q);
  },
  subir: (carrera, curso, archivo) => {
    const fd = new FormData();
    fd.append("carrera", carrera);
    fd.append("archivo", archivo);
    if (curso) fd.append("curso", curso);
    return pedir("/documentos", { method: "POST", body: fd });
  },
  borrar: (id) => pedir(`/documentos/${id}`, { method: "DELETE" }),
  versiones: (id) => pedir(`/documentos/${id}/versiones`),
  cambiarEstado: (id, activo) =>
    pedir(`/documentos/${id}/estado`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activo }),
    }),

  // bitacora (solo coord)
  logs: () => pedir("/logs"),

  // metricas (coord: sin curso -> global de la carrera; docente: siempre con curso)
  metricas: (carrera, curso) => {
    const q = new URLSearchParams();
    if (carrera) q.append("carrera", carrera);
    if (curso) q.append("curso", curso);
    return pedir("/metricas?" + q);
  },

  // visor PDF
  urlPagina: (ref, pagina) => {
    const t = getToken();
    return BASE + "/documentos/pagina?" + new URLSearchParams({ ref, pagina })
      + (t ? "&_t=" + encodeURIComponent(t) : "");
  },
  infoDoc: (ref) => pedir("/documentos/info?" + new URLSearchParams({ ref })),

  // ---------- gestion de usuarios (solo coord) ----------
  usuarios: {
    listar: () => pedir("/usuarios"),
    crear: (u) =>
      pedir("/usuarios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(u),
      }),
    actualizar: (usuario, cambios) =>
      pedir(`/usuarios/${encodeURIComponent(usuario)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cambios),
      }),
    borrar: (usuario) =>
      pedir(`/usuarios/${encodeURIComponent(usuario)}`, { method: "DELETE" }),
  },
};
