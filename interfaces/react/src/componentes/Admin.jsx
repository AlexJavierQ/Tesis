import { useEffect, useState } from "react";
import { api } from "../api";

/**
 * Panel de gestion para docente y coordinacion, con 3 pestanas:
 *   - Documentos: subir / borrar / listar PDFs
 *   - Cursos: crear cursos nuevos (docente y coord)
 *   - Metricas: ver estadisticas
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

  useEffect(() => { recargarCursos(); }, [carrera]);
  useEffect(() => { recargarDocs(); }, [curso, pestana]);

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
    </div>
  );
}
