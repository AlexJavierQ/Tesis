import { useEffect, useState } from "react";
import { api } from "../../api";
import { cursosGestionables } from "./cursos";

/**
 * Metricas agregadas (nunca muestran quien pregunto).
 * Coordinacion: toda la carrera. Docente: uno de sus cursos asignados.
 */
export default function Metricas({ usuario, carrera, fallar }) {
  const esCoord = usuario.rol === "coordinacion";
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");
  const [metricas, setMetricas] = useState(null);

  useEffect(() => {
    if (esCoord) return;
    cursosGestionables(usuario, carrera).then((cs) => {
      setCursos(cs);
      setCurso(cs[0] || "");
    }).catch((e) => fallar(e.message));
  }, [carrera]);

  async function cargar() {
    try { setMetricas(await api.metricas(carrera, esCoord ? null : curso)); }
    catch (e) { fallar(e.message); }
  }

  return (
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
              {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
        </div>
      )}

      <button onClick={cargar} disabled={!esCoord && !curso}>🔄 Cargar métricas</button>

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

          <h4>Temas más consultados</h4>
          <p className="admin-nota">
            Agrupados por significado: preguntas escritas distinto pero que
            significan lo mismo cuentan como un solo tema.
          </p>
          {metricas.top.length === 0
            ? <p className="vacio">—</p>
            : <ul className="met-lista">
                {metricas.top.map((t, i) => (
                  <li key={i}>
                    <span>
                      {t.pregunta}
                      {t.variantes > 1 &&
                        <em className="met-variantes"> · {t.variantes} formas distintas</em>}
                    </span>
                    <em>{t.n}</em>
                  </li>
                ))}
              </ul>}

          <h4>Preguntas sin respaldo (vacíos a cubrir)</h4>
          {metricas.sin_respaldo.length === 0
            ? <p className="vacio">Ninguna. 🎉</p>
            : <ul className="met-lista">
                {metricas.sin_respaldo.map((p, i) => <li key={i}><span>{p}</span></li>)}
              </ul>}
        </div>
      )}
    </section>
  );
}
