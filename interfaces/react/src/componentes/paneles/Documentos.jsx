import { useEffect, useRef, useState } from "react";
import {
  FileText, Upload, History, Power, Trash2, RotateCcw, FolderOpen, Library, BookOpen, GraduationCap,
  CalendarRange, Pencil,
} from "lucide-react";
import { api } from "../../api";
import { fecha, nombre, plural } from "../../formato";
import { Encabezado, Tarjeta, Insignia, Vacio } from "../ui";

/**
 * Documentos que usa el asistente, organizados por carrera.
 *  - izquierda: indice de ambitos agrupado por carrera
 *      coordinacion -> reglamentos generales + cada curso de sus carreras
 *      docente      -> solo sus cursos asignados
 *  - derecha: los documentos del ambito elegido (subir, versiones,
 *    restaurar, activar/desactivar, eliminar)
 */
export default function Documentos({ usuario, avisar, fallar }) {
  const esCoord = usuario.rol === "coordinacion";
  const [grupos, setGrupos] = useState([]);       // [{carrera, ambitos: [{carrera, curso}]}]
  const [ambito, setAmbito] = useState(null);     // {carrera, curso|null}
  const [docs, setDocs] = useState([]);
  const [versiones, setVersiones] = useState({}); // docId -> versiones (si esta abierta)
  const [subiendo, setSubiendo] = useState(false);
  const selectorArchivo = useRef(null);

  // arma el indice de ambitos segun el rol
  useEffect(() => {
    (async () => {
      try {
        let lista;
        if (esCoord) {
          lista = await Promise.all(usuario.carreras.map(async (c) => ({
            carrera: c,
            ambitos: [{ carrera: c, curso: null },
                      ...(await api.cursos(c)).map((cu) => ({ carrera: c, curso: cu }))],
          })));
        } else {
          lista = usuario.carreras
            .map((c) => ({
              carrera: c,
              ambitos: usuario.cursos_asignados.filter((a) => a.carrera === c),
            }))
            .filter((g) => g.ambitos.length);
        }
        setGrupos(lista);
        setAmbito(lista[0]?.ambitos[0] || null);
      } catch (e) { fallar(e.message); }
    })();
  }, []);

  useEffect(() => { recargar(); }, [ambito]);

  async function recargar() {
    if (!ambito) { setDocs([]); return; }
    try {
      setDocs(await api.documentos(ambito.carrera, ambito.curso));
      setVersiones({});
    } catch (e) { fallar(e.message); }
  }

  async function subir(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setSubiendo(true);
    try {
      const r = await api.subir(ambito.carrera, ambito.curso, f);
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

  async function editarVigencia(d) {
    const texto = prompt(
      `Vigencia o período de "${d.nombre}".\n` +
      "El asistente la menciona cuando cita fechas o plazos de este documento.\n" +
      "Ejemplo: Período abril-agosto 2024 (fechas históricas)",
      d.vigencia);
    if (texto === null) return;
    try {
      await api.cambiarVigencia(d.id, texto);
      avisar(`Vigencia de "${d.nombre}" actualizada.`);
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

  const totalAmbitos = grupos.reduce((n, g) => n + g.ambitos.length, 0);
  const igual = (a, b) => a && b && a.carrera === b.carrera && a.curso === b.curso;

  if (totalAmbitos === 0) {
    return (
      <>
        <Encabezado titulo="Documentos" descripcion="Los PDF que el asistente usa para responder." />
        <Tarjeta>
          <Vacio icono={BookOpen} titulo="Aún no tienes cursos asignados">
            Cuando la coordinación te asigne un curso, aquí podrás subir su material.
          </Vacio>
        </Tarjeta>
      </>
    );
  }

  const panel = ambito && (
    <Tarjeta>
      <div className="ambito-cabecera">
        <div>
          <h2>{ambito.curso || "Reglamentos generales"}</h2>
          <p>{ambito.curso
            ? `Material del curso en ${nombre(ambito.carrera)}. Se usa cuando el estudiante pregunta desde este curso.`
            : `Normativa de ${nombre(ambito.carrera)}. Se usa en todas las respuestas de la carrera.`}</p>
        </div>
        <input ref={selectorArchivo} type="file" accept="application/pdf" hidden onChange={subir} />
        <button className="btn btn-primario" disabled={subiendo}
                title="Si ya existe un archivo con el mismo nombre, se guarda como versión nueva"
                onClick={() => selectorArchivo.current.click()}>
          <Upload size={18} />{subiendo ? "Subiendo…" : "Subir PDF"}
        </button>
      </div>

      {docs.length === 0
        ? <Vacio icono={FolderOpen} titulo="Todavía no hay documentos aquí">
            Sube un PDF. Si más adelante subes otro con el mismo nombre, se guarda como versión nueva.
          </Vacio>
        : <ul className="filas">
            {docs.map((d) => (
              <li key={d.id}>
                <div className={"fila" + (d.activo ? "" : " apagada")}>
                  <div className="fila-icono"><FileText size={20} /></div>
                  <div className="fila-cuerpo">
                    <div className="fila-titulo" title={d.nombre}>{d.nombre}</div>
                    <div className="fila-meta">
                      <span>Versión {d.version}</span>
                      <span>{plural(d.fragmentos, "fragmento")}</span>
                      <span>Actualizado el {fecha(d.subido_en)}</span>
                    </div>
                  </div>
                  {d.activo ? <Insignia tipo="exito">Activo</Insignia> : <Insignia>Desactivado</Insignia>}
                  <div className="fila-acciones-derecha">
                    <button className="btn btn-secundario btn-chico" onClick={() => verVersiones(d)}
                            aria-expanded={Boolean(versiones[d.id])}>
                      <History size={15} />Versiones ({d.versiones})
                    </button>
                    <button className="btn btn-fantasma btn-chico" onClick={() => cambiarEstado(d)}>
                      <Power size={15} />{d.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button className="btn btn-peligro btn-icono" title="Eliminar documento"
                            aria-label={`Eliminar ${d.nombre}`} onClick={() => eliminar(d)}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                <div className="vigencia">
                  <CalendarRange size={15} />
                  <span><b>Vigencia:</b> {d.vigencia || "sin indicar"}</span>
                  <button className="btn btn-fantasma btn-chico" onClick={() => editarVigencia(d)}
                          aria-label={`Editar la vigencia de ${d.nombre}`}>
                    <Pencil size={13} />Editar
                  </button>
                </div>

                {versiones[d.id] && (
                  <div className="subpanel">
                    <ul className="filas">
                      {versiones[d.id].map((v) => (
                        <li key={v.numero} className="fila">
                          <div className="fila-cuerpo">
                            <div className="fila-titulo">Versión {v.numero}</div>
                            <div className="fila-meta">
                              <span>{fecha(v.subido_en)}</span>
                              <span>Subida por {v.subido_por}</span>
                              {v.restaurada_de && <span>Copia de la versión {v.restaurada_de}</span>}
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
  );

  return (
    <>
      <Encabezado titulo="Documentos"
                  descripcion="Los PDF que el asistente usa para responder. Solo los documentos activos cuentan." />
      {totalAmbitos === 1
        ? panel
        : <div className="con-indice">
            <nav className="indice" aria-label="Ámbitos de documentos">
              {grupos.map((g) => (
                <div key={g.carrera} className="indice-grupo">
                  <div className="indice-titulo"><GraduationCap size={15} />{nombre(g.carrera)}</div>
                  {g.ambitos.map((a) => (
                    <button key={a.curso || "general"}
                            className={"indice-item" + (igual(a, ambito) ? " activo" : "")}
                            aria-current={igual(a, ambito) ? "true" : undefined}
                            onClick={() => setAmbito(a)}>
                      {a.curso ? <BookOpen size={17} /> : <Library size={17} />}
                      {a.curso || "Reglamentos generales"}
                    </button>
                  ))}
                </div>
              ))}
            </nav>
            {panel}
          </div>}
    </>
  );
}
