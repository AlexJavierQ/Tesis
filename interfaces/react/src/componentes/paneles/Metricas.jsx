import { useEffect, useState } from "react";
import { RotateCcw, ChartColumn, CircleCheck, ShieldCheck, FlaskConical } from "lucide-react";
import { api } from "../../api";
import { dia, nombre, plural } from "../../formato";
import { cursosGestionables } from "./cursosGestionables";
import { Encabezado, Tarjeta, Vacio } from "../ui";

/**
 * Analisis de consultas con datos minimizados.
 * El servidor solo guarda la CATEGORIA de cada consulta (vocabulario cerrado):
 * aqui no hay preguntas literales ni usuarios, solo agregados.
 *  - Coordinacion: toda la carrera activa, o uno de sus cursos.
 *  - Docente: uno de sus cursos asignados.
 */
export default function Metricas({ usuario, carrera, fallar }) {
  const esCoord = usuario.rol === "coordinacion";
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");       // "" = toda la carrera (solo coordinacion)
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    cursosGestionables(usuario, carrera).then((cs) => {
      setCursos(cs);
      const inicial = esCoord ? "" : cs[0] || "";
      setCurso(inicial);
      if (esCoord || inicial) cargar(inicial);
    }).catch((e) => fallar(e.message));
  }, [carrera]);

  async function cargar(c) {
    setCargando(true);
    try { setDatos(await api.metricas(carrera, c || null)); }
    catch (e) { setDatos(null); fallar(e.message); }
    finally { setCargando(false); }
  }

  const maximo = datos?.categorias[0]?.total || 1;

  return (
    <>
      <Encabezado titulo="Análisis de consultas"
                  descripcion={esCoord
                    ? `Qué temas consultan los estudiantes de ${nombre(carrera)} y dónde falta respaldo documental.`
                    : "Qué temas consultan los estudiantes en tus cursos."}>
        {(esCoord || cursos.length > 0) && (
          <select value={curso} style={{ width: 220 }} aria-label="Ámbito"
                  onChange={(e) => { setCurso(e.target.value); cargar(e.target.value); }}>
            {esCoord && <option value="">Toda la carrera</option>}
            {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
        <button className="btn btn-secundario" disabled={cargando || (!esCoord && !curso)}
                onClick={() => cargar(curso)}>
          <RotateCcw size={16} />{cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </Encabezado>

      <p className="nota nota-bloque">
        <ShieldCheck size={17} />
        <span>Datos minimizados: de cada consulta solo se guarda su categoría, si tuvo respaldo
          y el día. No se almacenan las preguntas ni quién las hizo.</span>
      </p>

      {!esCoord && cursos.length === 0 && (
        <Tarjeta><Vacio icono={ChartColumn} titulo="No tienes cursos asignados">
          Cuando la coordinación te asigne un curso, aquí verás qué temas consultan sus estudiantes.
        </Vacio></Tarjeta>
      )}

      {datos && datos.total === 0 && (
        <Tarjeta><Vacio icono={ChartColumn} titulo="Aún no hay consultas registradas">
          Cuando los estudiantes usen el chat, aquí verás las categorías más consultadas.
        </Vacio></Tarjeta>
      )}

      {datos && datos.total > 0 && (
        <>
          {datos.sinteticas > 0 && (
            <p className="nota aviso nota-bloque">
              <FlaskConical size={17} />
              <span>{plural(datos.sinteticas, "consulta")} de este ámbito
                {datos.sinteticas === 1 ? " es un dato sintético" : " son datos sintéticos"} de
                demostración, no consultas reales de estudiantes.</span>
            </p>
          )}

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
              <dt>Sin respaldo documental</dt>
              <dd className={datos.sin_respaldo ? "atencion" : "bien"}>
                {datos.sin_respaldo}<small>{datos.sin_respaldo === 1 ? "consulta" : "consultas"}</small>
              </dd>
            </div>
          </dl>

          <div className="dos-columnas">
            <Tarjeta titulo="Categorías más consultadas"
                     descripcion={`Del ${dia(datos.desde)} al ${dia(datos.hasta)}. Cada consulta cuenta en una sola categoría.`}>
              {datos.categorias.map((c) => (
                <div key={c.clave} className="tema">
                  <div className="tema-cabecera">
                    <span className="tema-texto">{c.etiqueta}</span>
                    <span className="tema-n">{c.total}</span>
                  </div>
                  <div className="barra-progreso" aria-hidden="true">
                    <span style={{ width: `${(100 * c.total) / maximo}%` }} />
                  </div>
                </div>
              ))}
            </Tarjeta>

            <Tarjeta titulo="Brechas documentales"
                     descripcion="Categorías con consultas que el asistente no pudo responder con los documentos. Indican qué información conviene incorporar.">
              {datos.brechas.length === 0
                ? <Vacio icono={CircleCheck} titulo="Sin brechas por ahora">Todas las consultas tuvieron respaldo.</Vacio>
                : datos.brechas.map((b) => (
                    <div key={b.clave} className="tema">
                      <div className="tema-cabecera">
                        <span className="tema-texto">{b.etiqueta}</span>
                        <span className="tema-n atencion">{b.sin_respaldo} de {b.total}</span>
                      </div>
                      <div className="tema-meta">{b.pct_sin_respaldo} % de sus consultas quedó sin respaldo</div>
                      <div className="barra-progreso aviso" aria-hidden="true">
                        <span style={{ width: `${b.pct_sin_respaldo}%` }} />
                      </div>
                    </div>
                  ))}
            </Tarjeta>
          </div>

          {datos.ambitos.length > 0 && (
            <Tarjeta titulo="Consultas por ámbito" className="tarjeta-ambitos"
                     descripcion="Normativa general de la carrera y cada uno de sus cursos.">
              <div className="tabla-envoltura">
                <table className="tabla">
                  <thead>
                    <tr><th scope="col">Ámbito</th><th scope="col">Consultas</th><th scope="col">Sin respaldo</th></tr>
                  </thead>
                  <tbody>
                    {datos.ambitos.map((a) => (
                      <tr key={a.curso || "general"}>
                        <td>{a.curso || "Normativa general"}</td>
                        <td>{a.total}</td>
                        <td className={a.sin_respaldo ? "atencion" : ""}>{a.sin_respaldo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Tarjeta>
          )}
        </>
      )}
    </>
  );
}
