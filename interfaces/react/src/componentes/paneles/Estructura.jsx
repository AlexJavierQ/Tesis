import { useEffect, useState } from "react";
import { api } from "../../api";

/**
 * Estructura academica (solo coordinacion): de facultad hacia abajo.
 *  - crear facultades y carreras
 *  - crear cursos en la carrera activa
 *  - asignar a cada curso los docentes que lo dictan
 */
export default function Estructura({ carrera, avisar, fallar, refrescarUsuario }) {
  const [facultades, setFacultades] = useState([]);
  const [cursos, setCursos] = useState([]);
  const [docentesCarrera, setDocentesCarrera] = useState([]);  // docentes de esta carrera
  const [asignados, setAsignados] = useState({});              // curso -> [usuarios]
  const [editando, setEditando] = useState(null);              // curso cuyo equipo se edita
  const [nuevaFacultad, setNuevaFacultad] = useState("");
  const [nuevaCarrera, setNuevaCarrera] = useState({ nombre: "", facultad: "" });
  const [nuevoCurso, setNuevoCurso] = useState("");

  useEffect(() => { cargar(); }, [carrera]);

  async function cargar() {
    try {
      const fs = await api.facultades();
      setFacultades(fs);
      setNuevaCarrera((n) => ({ ...n, facultad: n.facultad || fs[0]?.nombre || "" }));
      const cs = await api.cursos(carrera);
      setCursos(cs);
      const usuarios = await api.usuarios.listar();
      setDocentesCarrera(usuarios
        .filter((u) => u.rol === "docente" && u.activo && u.carreras.includes(carrera))
        .map((u) => u.usuario));
      const mapa = {};
      for (const c of cs) mapa[c] = await api.docentesCurso(carrera, c);
      setAsignados(mapa);
    } catch (e) { fallar(e.message); }
  }

  async function crearFacultad() {
    try {
      await api.crearFacultad(nuevaFacultad.trim());
      avisar(`Facultad "${nuevaFacultad.trim()}" creada.`);
      setNuevaFacultad("");
      cargar();
    } catch (e) { fallar(e.message); }
  }

  async function crearCarrera() {
    try {
      await api.crearCarrera(nuevaCarrera.nombre.trim(), nuevaCarrera.facultad);
      avisar(`Carrera "${nuevaCarrera.nombre.trim()}" creada y asignada a ti. ` +
             "Elígela arriba a la derecha para gestionarla.");
      setNuevaCarrera({ ...nuevaCarrera, nombre: "" });
      refrescarUsuario();
      cargar();
    } catch (e) { fallar(e.message); }
  }

  async function crearCurso() {
    try {
      await api.crearCurso(carrera, nuevoCurso.trim());
      avisar(`Curso "${nuevoCurso.trim()}" creado. Ahora asígnale docentes.`);
      setNuevoCurso("");
      cargar();
    } catch (e) { fallar(e.message); }
  }

  function marcar(curso, docente) {
    const lista = asignados[curso] || [];
    setAsignados({
      ...asignados,
      [curso]: lista.includes(docente) ? lista.filter((d) => d !== docente) : [...lista, docente],
    });
  }

  async function guardarDocentes(curso) {
    try {
      await api.asignarDocentes(carrera, curso, asignados[curso] || []);
      avisar(`Docentes de "${curso}" actualizados.`);
      setEditando(null);
    } catch (e) { fallar(e.message); }
  }

  const facultadActual = facultades.find((f) => f.carreras.includes(carrera))?.nombre;

  return (
    <section className="admin-seccion">
      <h3>Estructura académica</h3>
      <p className="admin-nota">
        {facultadActual && <>Facultad de {facultadActual} › carrera <b>{carrera}</b>. </>}
        La coordinación crea los cursos y asigna a los docentes; cada docente
        solo gestiona los documentos de sus cursos.
      </p>

      <h4>Cursos de {carrera} ({cursos.length})</h4>
      <div className="fila">
        <label>Nuevo curso:
          <input value={nuevoCurso} onChange={(e) => setNuevoCurso(e.target.value)}
                 placeholder="Nombre del curso"
                 onKeyDown={(e) => e.key === "Enter" && nuevoCurso.trim() && crearCurso()} />
        </label>
        <button onClick={crearCurso} disabled={!nuevoCurso.trim()}>Crear curso</button>
      </div>

      {cursos.length === 0
        ? <p className="vacio">Aún no hay cursos creados.</p>
        : <ul className="doc-lista">
            {cursos.map((c) => (
              <li key={c}>
                <div className="doc-fila">
                  <span>
                    📚 {c} · docentes: {(asignados[c] || []).join(", ") || <em>sin asignar</em>}
                  </span>
                  <div className="doc-acciones">
                    {editando === c
                      ? <button className="btn-secundario" onClick={() => guardarDocentes(c)}>Guardar</button>
                      : <button className="btn-secundario" onClick={() => setEditando(c)}>Asignar docentes</button>}
                  </div>
                </div>
                {editando === c && (
                  <div className="fila checks">
                    {docentesCarrera.length === 0
                      ? <span>No hay docentes en esta carrera. Créalos en la pestaña Usuarios.</span>
                      : docentesCarrera.map((d) => (
                          <label key={d}>
                            <input type="checkbox" checked={(asignados[c] || []).includes(d)}
                                   onChange={() => marcar(c, d)} /> {d}
                          </label>
                        ))}
                  </div>
                )}
              </li>
            ))}
          </ul>}

      <h4>Facultades y carreras</h4>
      <ul className="doc-lista">
        {facultades.map((f) => (
          <li key={f.nombre}><span>🏛️ {f.nombre}: {f.carreras.join(", ") || "sin carreras"}</span></li>
        ))}
      </ul>
      <div className="fila">
        <label>Nueva facultad:
          <input value={nuevaFacultad} onChange={(e) => setNuevaFacultad(e.target.value)} />
        </label>
        <button onClick={crearFacultad} disabled={!nuevaFacultad.trim()}>Crear facultad</button>
      </div>
      <div className="fila">
        <label>Nueva carrera:
          <input value={nuevaCarrera.nombre}
                 onChange={(e) => setNuevaCarrera({ ...nuevaCarrera, nombre: e.target.value })} />
        </label>
        <label>En la facultad:
          <select value={nuevaCarrera.facultad}
                  onChange={(e) => setNuevaCarrera({ ...nuevaCarrera, facultad: e.target.value })}>
            {facultades.map((f) => <option key={f.nombre} value={f.nombre}>{f.nombre}</option>)}
          </select>
        </label>
        <button onClick={crearCarrera} disabled={!nuevaCarrera.nombre.trim()}>Crear carrera</button>
      </div>
    </section>
  );
}
