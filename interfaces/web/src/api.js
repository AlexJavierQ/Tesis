// Cliente de la API REST. Unico punto del frontend que sabe de HTTP:
// si cambia el backend, solo se toca este archivo.
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function pedir(ruta, opciones = {}) {
  const r = await fetch(`${BASE}${ruta}`, opciones);
  if (!r.ok) {
    let detalle = `Error ${r.status}`;
    try {
      const cuerpo = await r.json();
      if (cuerpo.detail) detalle = cuerpo.detail;
    } catch {
      /* respuesta sin cuerpo JSON: nos quedamos con el codigo */
    }
    throw new Error(detalle);
  }
  return r.json();
}

export const api = {
  salud: () => pedir("/salud"),

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

  preguntar: (pregunta, carrera, curso, historial) =>
    pedir("/preguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta, carrera, curso: curso || null, historial: historial || null }),
    }),

  documentos: (carrera, curso) => {
    const q = new URLSearchParams({ carrera });
    if (curso) q.append("curso", curso);
    return pedir(`/documentos?${q}`);
  },

  subirDocumento: (carrera, curso, archivo) => {
    const fd = new FormData();
    fd.append("carrera", carrera);
    fd.append("archivo", archivo);
    if (curso) fd.append("curso", curso);
    return pedir("/documentos", { method: "POST", body: fd });
  },

  borrarDocumento: (carrera, curso, nombre) => {
    const q = new URLSearchParams({ carrera, nombre });
    if (curso) q.append("curso", curso);
    return pedir(`/documentos?${q}`, { method: "DELETE" });
  },

  metricas: (carrera, curso) => {
    const q = new URLSearchParams();
    if (carrera) q.append("carrera", carrera);
    if (curso) q.append("curso", curso);
    return pedir(`/metricas?${q}`);
  },

  // URL directa de la imagen de una pagina (la usa <img> del visor)
  urlPagina: (ref, pagina) =>
    `${BASE}/documentos/pagina?${new URLSearchParams({ ref, pagina })}`,

  infoDocumento: (ref) =>
    pedir(`/documentos/info?${new URLSearchParams({ ref })}`),
};
