import { useEffect, useState } from "react";
import { api } from "../api";

/**
 * Panel de gestion para docente y coordinacion.
 * Docente: pestanas Documentos, Cursos y Metricas.
 * Coordinacion: ademas la pestana Usuarios (CRUD de usuarios).
 */
export default function Admin({ usuario }) {
  const esCoord = usuario.rol === "coordinacion";
  const carrera = usuario.carrera;

  const [pestana, setPestana] = useState("documentos");
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");
  const [docs, setDocs] = useState([]);
  const [metricas, setMetricas] = useState(null);
  const [aviso, setAviso] = useState(null);
  const [error, setError] = useState(null);
  const [nuevoCurso, setNuevoCurso] = useState("");

  // gestion de usuarios (solo coord)
  const [usuarios, setUsuarios] = useState([]);
  const [nuevoUsr, setNuevoUsr] = useState({
    usuario: "", password: "", rol: "estudiante", carrera: carrera,
  });

  useEffect(() => { recargarCursos(); }, [carrera]);
  useEffect(() => { recargarDocs(); }, [curso, pestana]);
  useEffect(() => {
    if (pestana === "usuarios" && esCoord) cargarUsuarios();
  }, [pestana]);

  async function recargarCursos() {
    try {
      const cs = await api.cursos(carrera);
      setCursos(cs);
      if (!esCoord && !curso && cs[0]) setCurso(cs[0]);
    } catch (e) { setError(e.message); }
  }

  async function recargarDocs() {
    if (pestana !== "documentos") return;
    setError(null);
    try {
      setDocs(await api.documentos(carrera, curso || null));
    } catch (e) { setError(e.message); }
  }

  async function subir(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setAviso(null); setError(null);
    try {
      const r = await api.subir(carrera, curso || null, f);
      setAviso(`"${r.archivo}" indexado (${r.fragmentos} fragmentos).`);
      recargarDocs();
    } catch (err) { setError(err.message); }
  }

  async function borrar(nombre) {
    if (!confirm(`Quitar "${nombre}"?`)) return;
    try {
      await api.borrar(carrera, curso || null, nombre);
      recargarDocs();
    } catch (err) { setError(err.message); }
  }

  async function crearCurso() {
    const nombre = nuevoCurso.trim();
    if (!nombre) return;
    setAviso(null); setError(null);
    try {
      await api.crearCurso(carrera, nombre);
      setNuevoCurso("");
      const cs = await api.cursos(carrera);
      setCursos(cs);
      setCurso(nombre);
      setAviso(`Curso "${nombre}" creado.`);
    } catch (e) { setError(e.message); }
  }

  // ---------- Gestion de usuarios (solo coord) ----------
  async function cargarUsuarios() {
    setError(null);
    try { setUsuarios(await api.usuarios.listar()); }
    catch (e) { setError(e.message); }
  }

  async function crearNuevoUsuario() {
    if (!nuevoUsr.usuario.trim() || !nuevoUsr.password.trim()) {
      setError("Usuario y contrasena obligatorios.");
      return;
    }
    setAviso(null); setError(null);
    try {
      await api.usuarios.crear(nuevoUsr);
      setAviso(`Usuario "${nuevoUsr.usuario}" creado.`);
      setNuevoUsr({ usuario: "", password: "", rol: "estudiante", carrera });
      cargarUsuarios();
    } catch (e) { setError(e.message); }
  }

  async function cambiarRolUsr(u, nuevoRol) {
    if (u.rol === nuevoRol) return;
    if (!confirm(`Cambiar rol de "${u.usuario}" a "${nuevoRol}"?`)) return;
    setAviso(null); setError(null);
    try {
      await api.usuarios.actualizar(u.usuario, { rol: nuevoRol });
      setAviso(`Rol de "${u.usuario}" actualizado a "${nuevoRol}".`);
      cargarUsuarios();
    } catch (e) { setError(e.message); }
  }

  async function resetearPasswordUsr(u) {
    const p = prompt(`Nueva contrasena para "${u.usuario}":`);
    if (!p || !p.trim()) return;
    setAviso(null); setError(null);
    try {
      await api.usuarios.actualizar(u.usuario, { nuevo_password: p });
      setAviso(`Contrasena de "${u.usuario}" reseteada. Sus sesiones activas fueron cerradas.`);
    } catch (e) { setError(e.message); }
  }

  async function borrarUsr(u) {
    if (u.usuario === usuario.usuario) {
      setError("No puedes borrarte a ti mismo.");
      return;
    }
    if (!confirm(`Borrar al usuario "${u.usuario}"? Esta accion es irreversible.`)) return;
    setAviso(null); setError(null);
    try {
      await api.usuarios.borrar(u.usuario);
      setAviso(`Usuario "${u.usuario}" borrado.`);
      cargarUsuarios();
    } catch (e) { setError(e.message); }
  }

  async function verMetricas() {
    setError(null);
    try {
      const dato = await api.metricas(carrera, esCoord ? null : (curso || null));
      setMetricas(dato);
    } catch (e) { setError(e.message); }
  }

  return (
    <div className="admin">
      <nav className="admin-tabs">
        <button
          className={pestana === "documentos" ? "activo" : ""}
          onClick={() => setPestana("documentos")}
        >📄 Documentos</button>
        <button
          className={pestana === "cursos" ? "activo" : ""}
          onClick={() => setPestana("cursos")}
        >📚 Cursos</button>
        <button
          className={pestana === "metricas" ? "activo" : ""}
          onClick={() => setPestana("metricas")}
        >📊 Métricas</button>
        {esCoord && (
          <button
            className={pestana === "usuarios" ? "activo" : ""}
            onClick={() => setPestana("usuarios")}
          >👥 Usuarios</button>
        )}
      </nav>

      {aviso && <div className="aviso-ok">{aviso}</div>}
      {error && <div className="aviso-error">{error}</div>}

      {pestana === "documentos" && (
        <section className="admin-seccion">
          <h3>Documentos</h3>
          <p className="admin-nota">
            {esCoord && !curso
              ? "Estás subiendo REGLAMENTOS GENERALES: afectan a toda la carrera."
              : `Estás subiendo documentos del curso "${curso || "(elige uno)"}".`}
          </p>

          <div className="fila">
            <label>Ámbito:
              <select value={curso} onChange={(e) => setCurso(e.target.value)}>
                {esCoord && <option value="">Reglamentos generales</option>}
                {cursos.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
            <label className="subir">
              <input type="file" accept="application/pdf" onChange={subir}
                     disabled={!esCoord && !curso} />
              <span>Subir PDF</span>
            </label>
          </div>

          <h4>Documentos actuales ({docs.length})</h4>
          {docs.length === 0
            ? <p className="vacio">Aún no hay documentos en este ámbito.</p>
            : <ul className="doc-lista">
                {docs.map(d => (
                  <li key={d.ref}>
                    <span>{d.nombre} · {d.paginas} pág.</span>
                    <button onClick={() => borrar(d.nombre)}>Quitar</button>
                  </li>
                ))}
              </ul>}
        </section>
      )}

      {pestana === "cursos" && (
        <section className="admin-seccion">
          <h3>Cursos de la carrera</h3>
          <p className="admin-nota">
            Cada curso tiene sus propios documentos que solo afectan al chat de ese curso.
          </p>

          <div className="fila">
            <label>Crear un curso nuevo:
              <input value={nuevoCurso}
                     onChange={(e) => setNuevoCurso(e.target.value)}
                     placeholder="Nombre del curso"
                     onKeyDown={(e) => e.key === "Enter" && crearCurso()} />
            </label>
            <button onClick={crearCurso} disabled={!nuevoCurso.trim()}>
              Crear curso
            </button>
          </div>

          <h4>Cursos existentes ({cursos.length})</h4>
          {cursos.length === 0
            ? <p className="vacio">Aún no hay cursos creados.</p>
            : <ul className="doc-lista">
                {cursos.map(c => (
                  <li key={c}>
                    <span>📚 {c}</span>
                    <button onClick={() => { setCurso(c); setPestana("documentos"); }}>
                      Ver documentos
                    </button>
                  </li>
                ))}
              </ul>}
        </section>
      )}

      {pestana === "metricas" && (
        <section className="admin-seccion">
          <h3>{esCoord ? "Métricas de la carrera" : "Métricas de tus cursos"}</h3>
          <p className="admin-nota">
            {esCoord
              ? "Vista global: todas las consultas hechas al asistente en tu carrera."
              : "Solo consultas hechas al asistente en el curso seleccionado."}
          </p>

          {!esCoord && (
            <div className="fila">
              <label>Curso:
                <select value={curso} onChange={(e) => setCurso(e.target.value)}>
                  {cursos.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
            </div>
          )}

          <button onClick={verMetricas} disabled={!esCoord && !curso}>
            🔄 Cargar métricas
          </button>

          {metricas && metricas.total === 0 && (
            <p className="vacio">Aún no hay consultas registradas en este ámbito.</p>
          )}

          {metricas && metricas.total > 0 && (
            <div className="met-cuerpo">
              <div className="met-tarjetas">
                <div className="met-tarjeta">
                  <span className="met-num">{metricas.total}</span>
                  <span className="met-lbl">consultas</span>
                </div>
                <div className="met-tarjeta">
                  <span className="met-num">{metricas.pct_respaldo}%</span>
                  <span className="met-lbl">con respaldo</span>
                </div>
                <div className="met-tarjeta">
                  <span className="met-num">{metricas.sin_respaldo.length}</span>
                  <span className="met-lbl">sin respaldo</span>
                </div>
              </div>

              <h4>Preguntas más frecuentes</h4>
              {metricas.top.length === 0
                ? <p className="vacio">—</p>
                : <ul className="met-lista">
                    {metricas.top.map((t, i) =>
                      <li key={i}><span>{t.pregunta}</span><em>{t.n}</em></li>)}
                  </ul>}

              <h4>Preguntas sin respaldo (vacíos a cubrir)</h4>
              {metricas.sin_respaldo.length === 0
                ? <p className="vacio">Ninguna. 🎉</p>
                : <ul className="met-lista">
                    {metricas.sin_respaldo.map((p, i) =>
                      <li key={i}><span>{p}</span></li>)}
                  </ul>}
            </div>
          )}
        </section>
      )}

      {pestana === "usuarios" && esCoord && (
        <section className="admin-seccion">
          <h3>Usuarios del sistema</h3>
          <p className="admin-nota">
            Solo la coordinación puede crear, modificar y eliminar usuarios.
            Cambiar la contraseña cierra todas las sesiones activas del usuario.
          </p>

          <h4>Crear nuevo usuario</h4>
          <div className="fila">
            <label>Usuario:
              <input
                value={nuevoUsr.usuario}
                onChange={(e) => setNuevoUsr({ ...nuevoUsr, usuario: e.target.value })}
                placeholder="ej: jperez"
              />
            </label>
            <label>Contraseña:
              <input
                type="password"
                value={nuevoUsr.password}
                onChange={(e) => setNuevoUsr({ ...nuevoUsr, password: e.target.value })}
              />
            </label>
            <label>Rol:
              <select
                value={nuevoUsr.rol}
                onChange={(e) => setNuevoUsr({ ...nuevoUsr, rol: e.target.value })}
              >
                <option value="estudiante">Estudiante</option>
                <option value="docente">Docente</option>
                <option value="coordinacion">Coordinación</option>
              </select>
            </label>
            <label>Carrera:
              <input
                value={nuevoUsr.carrera}
                onChange={(e) => setNuevoUsr({ ...nuevoUsr, carrera: e.target.value })}
              />
            </label>
            <button
              onClick={crearNuevoUsuario}
              disabled={!nuevoUsr.usuario.trim() || !nuevoUsr.password.trim()}
            >Crear usuario</button>
          </div>

          <h4>Usuarios existentes ({usuarios.length})</h4>
          {usuarios.length === 0
            ? <p className="vacio">Cargando o sin usuarios.</p>
            : <table className="tabla-usuarios">
                <thead>
                  <tr>
                    <th>Usuario</th>
                    <th>Rol</th>
                    <th>Carrera</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {usuarios.map(u => (
                    <tr key={u.usuario}>
                      <td>
                        {u.usuario}
                        {u.usuario === usuario.usuario && <span className="chip-yo"> (tú)</span>}
                      </td>
                      <td>
                        <select
                          value={u.rol}
                          onChange={(e) => cambiarRolUsr(u, e.target.value)}
                          disabled={u.usuario === usuario.usuario}
                        >
                          <option value="estudiante">Estudiante</option>
                          <option value="docente">Docente</option>
                          <option value="coordinacion">Coordinación</option>
                        </select>
                      </td>
                      <td>{u.carrera}</td>
                      <td>
                        <button
                          className="btn-secundario"
                          onClick={() => resetearPasswordUsr(u)}
                        >Resetear contraseña</button>
                        <button
                          className="btn-peligro"
                          onClick={() => borrarUsr(u)}
                          disabled={u.usuario === usuario.usuario}
                        >Borrar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>}
        </section>
      )}
    </div>
  );
}
