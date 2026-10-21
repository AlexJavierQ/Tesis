import { useEffect, useState } from "react";
import { MessagesSquare, CircleCheck, TriangleAlert, RotateCcw, ChartColumn, TrendingUp } from "lucide-react";
import { api } from "../../api";
import { cursosGestionables } from "./cursos";
import { Encabezado, Tarjeta, Vacio } from "../ui";

/**
 * Metricas agregadas (nunca muestran quien pregunto).
 * Coordinacion: toda la carrera. Docente: uno de sus cursos asignados.
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

  return (
    <>
      <Encabezado contexto={carrera} titulo="Métricas"
                  descripcion={esCoord
                    ? "Qué preguntan los estudiantes de la carrera y qué falta en los documentos."
                    : "Qué preguntan los estudiantes en tus cursos."}>
        {!esCoord && cursos.length > 0 && (
          <select value={curso} style={{ width: 200 }} aria-label="Curso"
                  onChange={(e) => { setCurso(e.target.value); cargar(e.target.value); }}>
            {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
        <button className="btn btn-secundario" disabled={cargando || (!esCoord && !curso)}
                onClick={() => cargar(curso)}>
          <RotateCcw size={16} />{cargando ? "Cargando…" : "Actualizar"}
        </button>
      </Encabezado>

      {!esCoord && cursos.length === 0 && (
        <Tarjeta><Vacio icono={ChartColumn} titulo="No tienes cursos asignados" /></Tarjeta>
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
          <div className="rejilla rejilla-3">
            <Dato icono={MessagesSquare} color="primario" numero={datos.total} etiqueta="consultas en total" />
            <Dato icono={CircleCheck} color="exito" numero={`${datos.pct_respaldo} %`}
                  etiqueta="respondidas con respaldo documental" />
            <Dato icono={TriangleAlert} color="aviso" numero={datos.sin_respaldo.length}
                  etiqueta="preguntas sin respuesta en los documentos" />
          </div>

          <div className="rejilla rejilla-2" style={{ marginTop: 24 }}>
            <Tarjeta titulo="Temas más consultados"
                     descripcion="Agrupados por significado: preguntas escritas distinto pero que significan lo mismo cuentan como un solo tema.">
              {datos.top.map((t, i) => (
                <div key={i} className="tema">
                  <div className="tema-cabecera">
                    <span className="tema-texto">{t.pregunta}</span>
                    <span className="tema-n">{t.n}</span>
                  </div>
                  {t.variantes > 1 && <div className="tema-meta">{t.variantes} formas distintas de preguntarlo</div>}
                  <div className="barra-progreso"><span style={{ width: `${(100 * t.n) / maximo}%` }} /></div>
                </div>
              ))}
            </Tarjeta>

            <Tarjeta titulo="Vacíos de información"
                     descripcion="Preguntas que el asistente no pudo responder con los documentos. Indican qué información conviene agregar.">
              {datos.sin_respaldo.length === 0
                ? <Vacio icono={TrendingUp} titulo="Ninguna">Todas las consultas tuvieron respaldo.</Vacio>
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

function Dato({ icono: Icono, color, numero, etiqueta }) {
  return (
    <div className="tarjeta dato">
      <div className="dato-icono" style={{ background: `var(--${color}-suave)`, color: `var(--${color})` }}>
        <Icono size={24} />
      </div>
      <div>
        <div className="dato-numero">{numero}</div>
        <div className="dato-etiqueta">{etiqueta}</div>
      </div>
    </div>
  );
}
