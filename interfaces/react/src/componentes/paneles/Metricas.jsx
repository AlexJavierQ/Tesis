import { useEffect, useState } from "react";
import { TriangleAlert, RotateCcw, ChartColumn, CircleCheck } from "lucide-react";
import { api } from "../../api";
import { nombre } from "../../formato";
import { cursosGestionables } from "./cursosGestionables";
import { Encabezado, Tarjeta, Vacio } from "../ui";

/**
 * Metricas agregadas (nunca muestran quien pregunto).
 * Coordinacion: toda la carrera activa. Docente: uno de sus cursos asignados.
 */
export default function Metricas({ usuario, carrera, fallar }) {
  const esCoord = usuario.rol === "coordinacion";
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (esCoord) { cargar(null); return; }
    cursosGestionables(usuario, carrera).then((cs) => {
      setCursos(cs);
      setCurso(cs[0] || "");
      if (cs[0]) cargar(cs[0]);
    }).catch((e) => fallar(e.message));
  }, [carrera]);

  async function cargar(c) {
    setCargando(true);
    try { setDatos(await api.metricas(carrera, esCoord ? null : c)); }
    catch (e) { fallar(e.message); }
    finally { setCargando(false); }
  }

  const maximo = datos?.top[0]?.n || 1;
  const sinRespuesta = datos?.sin_respaldo.length || 0;

  return (
    <>
      <Encabezado titulo="Métricas"
                  descripcion={esCoord
                    ? `Qué preguntan los estudiantes de ${nombre(carrera)} y qué falta en los documentos.`
                    : "Qué preguntan los estudiantes en tus cursos."}>
        {!esCoord && cursos.length > 0 && (
          <select value={curso} style={{ width: 200 }} aria-label="Curso"
                  onChange={(e) => { setCurso(e.target.value); cargar(e.target.value); }}>
            {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
        <button className="btn btn-secundario" disabled={cargando || (!esCoord && !curso)}
                onClick={() => cargar(curso)}>
          <RotateCcw size={16} />{cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </Encabezado>

      {!esCoord && cursos.length === 0 && (
        <Tarjeta><Vacio icono={ChartColumn} titulo="No tienes cursos asignados">
          Cuando la coordinación te asigne un curso, aquí verás qué preguntan sus estudiantes.
        </Vacio></Tarjeta>
      )}

      {!datos && cargando && (
        <Tarjeta><Vacio icono={ChartColumn} titulo="Calculando métricas…">
          Agrupando las consultas por significado. Puede tardar unos segundos.
        </Vacio></Tarjeta>
      )}

      {datos && datos.total === 0 && (
        <Tarjeta><Vacio icono={ChartColumn} titulo="Aún no hay consultas registradas">
          Cuando los estudiantes usen el chat, aquí verás sus temas más frecuentes.
        </Vacio></Tarjeta>
      )}

      {datos && datos.total > 0 && (
        <>
          <dl className="resumen">
            <div>
              <dt>Consultas</dt>
              <dd>{datos.total}</dd>
            </div>
            <div>
              <dt>Con respaldo en los documentos</dt>
              <dd className={datos.pct_respaldo >= 80 ? "bien" : "atencion"}>{datos.pct_respaldo} %</dd>
            </div>
            <div>
              <dt>Sin respuesta en los documentos</dt>
              <dd className={sinRespuesta ? "atencion" : "bien"}>
                {sinRespuesta}<small>{sinRespuesta === 1 ? "pregunta" : "preguntas"}</small>
              </dd>
            </div>
          </dl>

          <div className="dos-columnas">
            <Tarjeta titulo="Temas más consultados"
                     descripcion="Las preguntas que significan lo mismo, aunque estén escritas distinto, cuentan como un solo tema.">
              {datos.top.map((t, i) => (
                <div key={i} className="tema">
                  <div className="tema-cabecera">
                    <span className="tema-texto">{t.pregunta}</span>
                    <span className="tema-n">{t.n}</span>
                  </div>
                  {t.variantes > 1 && <div className="tema-meta">Preguntado de {t.variantes} formas distintas</div>}
                  <div className="barra-progreso" aria-hidden="true">
                    <span style={{ width: `${(100 * t.n) / maximo}%` }} />
                  </div>
                </div>
              ))}
            </Tarjeta>

            <Tarjeta titulo="Vacíos de información"
                     descripcion="Lo que el asistente no pudo responder con los documentos. Indica qué información conviene agregar.">
              {sinRespuesta === 0
                ? <Vacio icono={CircleCheck} titulo="Sin vacíos por ahora">Todas las consultas tuvieron respaldo.</Vacio>
                : <ul className="filas">
                    {datos.sin_respaldo.map((p, i) => (
                      <li key={i} className="fila">
                        <TriangleAlert size={17} style={{ color: "var(--aviso)", flexShrink: 0 }} />
                        <span className="fila-cuerpo">{p}</span>
                      </li>
                    ))}
                  </ul>}
            </Tarjeta>
          </div>
        </>
      )}
    </>
  );
}
