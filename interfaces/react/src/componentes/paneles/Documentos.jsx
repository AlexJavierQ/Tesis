import { useEffect, useRef, useState } from "react";
import { FileText, Upload, History, Power, Trash2, RotateCcw, Info, FolderOpen } from "lucide-react";
import { api } from "../../api";
import { cursosGestionables } from "./cursos";
import { Encabezado, Tarjeta, Insignia, Vacio } from "../ui";

/**
 * Documentos de un ambito: subir (o subir nueva version), ver versiones,
 * restaurar una version anterior, activar/desactivar y eliminar.
 * Coordinacion: reglamentos generales + cualquier curso.
 * Docente: solo sus cursos asignados.
 */
export default function Documentos({ usuario, carrera, avisar, fallar }) {
  const esCoord = usuario.rol === "coordinacion";
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");          // "" = reglamentos generales
  const [docs, setDocs] = useState([]);
  const [versiones, setVersiones] = useState({});  // docId -> versiones (si esta abierta)
  const [subiendo, setSubiendo] = useState(false);
  const selectorArchivo = useRef(null);

  useEffect(() => {
    cursosGestionables(usuario, carrera).then((cs) => {
      setCursos(cs);
      if (!esCoord) setCurso(cs[0] || "");          // el docente no tiene "generales"
    }).catch((e) => fallar(e.message));
  }, [carrera]);

  useEffect(() => { recargar(); }, [curso, cursos]);

  const sinAmbito = !esCoord && !curso;              // docente sin cursos asignados

  async function recargar() {
    if (sinAmbito) { setDocs([]); return; }
    try {
      setDocs(await api.documentos(carrera, curso || null));
      setVersiones({});
    } catch (e) { fallar(e.message); }
  }

  async function subir(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setSubiendo(true);
    try {
      const r = await api.subir(carrera, curso || null, f);
      avisar(r.version > 1
        ? `"${r.archivo}" actualizado a la versión ${r.version}. La anterior quedó guardada.`
        : `"${r.archivo}" subido e indexado (${r.fragmentos} fragmentos).`);
      recargar();
    } catch (err) { fallar(err.message); }
    finally { setSubiendo(false); }
  }

  async function eliminar(d) {
    if (!confirm(`¿Eliminar "${d.nombre}" con todas sus versiones? No se puede deshacer.`)) return;
    try {
      await api.borrar(d.id);
      avisar(`"${d.nombre}" eliminado.`);
      recargar();
    } catch (err) { fallar(err.message); }
  }

  async function cambiarEstado(d) {
    try {
      await api.cambiarEstado(d.id, !d.activo);
      avisar(d.activo
        ? `"${d.nombre}" desactivado: el asistente ya no lo usa.`
        : `"${d.nombre}" activado: el asistente vuelve a usarlo.`);
      recargar();
    } catch (err) { fallar(err.message); }
  }

  async function verVersiones(d) {
    if (versiones[d.id]) {                         // si ya esta abierta, se cierra
      const copia = { ...versiones };
      delete copia[d.id];
      setVersiones(copia);
      return;
    }
    try { setVersiones({ ...versiones, [d.id]: await api.versiones(d.id) }); }
    catch (err) { fallar(err.message); }
  }

  async function restaurar(d, numero) {
    if (!confirm(`¿Volver a la versión ${numero} de "${d.nombre}"?\n\n` +
                 "Se creará una versión nueva con ese contenido. No se borra ninguna versión.")) return;
    try {
      const r = await api.restaurar(d.id, numero);
      avisar(`Se restauró la versión ${numero} como versión ${r.version}.`);
      recargar();
    } catch (err) { fallar(err.message); }
  }

  const nombreAmbito = curso ? `el curso ${curso}` : "los reglamentos generales";

  return (
    <>
      <Encabezado contexto={carrera} titulo="Documentos"
                  descripcion="Los PDF que el asistente usa para responder. Solo se usan los documentos activos.">
        <input ref={selectorArchivo} type="file" accept="application/pdf" hidden onChange={subir} />
        <button className="btn btn-primario" disabled={sinAmbito || subiendo}
                onClick={() => selectorArchivo.current.click()}>
          <Upload size={18} />{subiendo ? "Subiendo…" : "Subir PDF"}
        </button>
      </Encabezado>

      <Tarjeta titulo="Ámbito" descripcion="Elige a qué conjunto de documentos quieres agregar o revisar.">
        {sinAmbito
          ? <div className="nota aviso"><Info size={16} />
              Aún no tienes cursos asignados. Pide a la coordinación que te asigne uno.</div>
          : <div className="rejilla-campos">
              <label className="campo">
                <span>Ámbito</span>
                <select value={curso} onChange={(e) => setCurso(e.target.value)}>
                  {esCoord && <option value="">Reglamentos generales de la carrera</option>}
                  {cursos.map((c) => <option key={c} value={c}>Curso: {c}</option>)}
                </select>
              </label>
              <div className="nota"><Info size={16} />
                <span>{curso
                  ? "Estos documentos solo se usan cuando el estudiante pregunta desde este curso."
                  : "Estos documentos afectan las respuestas de toda la carrera."}{" "}
                  Si subes un PDF con un nombre que ya existe, se guarda como versión nueva.</span>
              </div>
            </div>}
      </Tarjeta>

      <Tarjeta titulo={`Documentos de ${nombreAmbito}`}
               descripcion={`${docs.length} documento${docs.length === 1 ? "" : "s"}`}>
        {docs.length === 0
          ? <Vacio icono={FolderOpen} titulo="No hay documentos en este ámbito">
              Usa el botón «Subir PDF» para agregar el primero.
            </Vacio>
          : <ul className="filas">
              {docs.map((d) => (
                <li key={d.id}>
                  <div className={"fila" + (d.activo ? "" : " apagada")}>
                    <div className="fila-icono"><FileText size={20} /></div>
                    <div className="fila-cuerpo">
                      <div className="fila-titulo">{d.nombre}</div>
                      <div className="fila-meta">
                        <span>Versión {d.version}</span>·<span>{d.fragmentos} fragmentos</span>·
                        <span>Actualizado {d.subido_en.slice(0, 16)}</span>
                      </div>
                    </div>
                    {d.activo
                      ? <Insignia tipo="exito">Activo</Insignia>
                      : <Insignia>Desactivado</Insignia>}
                    <div className="fila-acciones-derecha">
                      <button className="btn btn-secundario btn-chico" onClick={() => verVersiones(d)}>
                        <History size={15} />Versiones ({d.versiones})
                      </button>
                      <button className="btn btn-fantasma btn-chico" onClick={() => cambiarEstado(d)}>
                        <Power size={15} />{d.activo ? "Desactivar" : "Activar"}
                      </button>
                      <button className="btn btn-peligro btn-icono" title="Eliminar documento"
                              onClick={() => eliminar(d)}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>

                  {versiones[d.id] && (
                    <div className="subpanel">
                      <ul className="filas">
                        {versiones[d.id].map((v) => (
                          <li key={v.numero} className="fila">
                            <div className="fila-cuerpo">
                              <div className="fila-titulo">Versión {v.numero}</div>
                              <div className="fila-meta">
                                <span>{v.subido_en.slice(0, 16)}</span>·<span>subida por {v.subido_por}</span>
                                {v.restaurada_de && <>·<span>restaurada desde la versión {v.restaurada_de}</span></>}
                              </div>
                            </div>
                            {v.numero === d.version
                              ? <Insignia tipo="primario">Vigente</Insignia>
                              : <button className="btn btn-secundario btn-chico" onClick={() => restaurar(d, v.numero)}>
                                  <RotateCcw size={15} />Restaurar
                                </button>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </li>
              ))}
            </ul>}
      </Tarjeta>
    </>
  );
}
