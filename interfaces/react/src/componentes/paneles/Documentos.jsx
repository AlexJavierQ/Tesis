import { useEffect, useState } from "react";
import { api } from "../../api";
import { cursosGestionables } from "./cursos";

/**
 * Documentos de un ambito: subir (o subir nueva version), ver versiones,
 * restaurar una version anterior, activar/desactivar y quitar.
 * Coordinacion: reglamentos generales + cualquier curso.
 * Docente: solo sus cursos asignados.
 */
export default function Documentos({ usuario, carrera, avisar, fallar }) {
  const esCoord = usuario.rol === "coordinacion";
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");          // "" = reglamentos generales
  const [docs, setDocs] = useState([]);
  const [versiones, setVersiones] = useState({});  // docId -> versiones (si esta abierta)

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
    try {
      const r = await api.subir(carrera, curso || null, f);
      avisar(r.version > 1
        ? `"${r.archivo}" actualizado a la versión ${r.version}. La anterior quedó de respaldo.`
        : `"${r.archivo}" indexado (${r.fragmentos} fragmentos).`);
      recargar();
    } catch (err) { fallar(err.message); }
  }

  async function borrar(d) {
    if (!confirm(`¿Quitar "${d.nombre}" con todas sus versiones?`)) return;
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
        ? `"${d.nombre}" desactivado: el chat ya no lo usa.`
        : `"${d.nombre}" activado de nuevo.`);
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
    if (!confirm(`¿Volver a la versión ${numero} de "${d.nombre}"? ` +
                 `Se creará una versión nueva con ese contenido; no se borra ninguna.`)) return;
    try {
      const r = await api.restaurar(d.id, numero);
      avisar(`Restaurada la v${numero} como v${r.version}.`);
      recargar();
    } catch (err) { fallar(err.message); }
  }

  return (
    <section className="admin-seccion">
      <h3>Documentos</h3>
      <p className="admin-nota">
        {sinAmbito
          ? "Aún no tienes cursos asignados. Pide a la coordinación que te asigne uno."
          : esCoord && !curso
            ? "Estás en REGLAMENTOS GENERALES: afectan a toda la carrera."
            : `Estás en el curso "${curso}".`}
        {" "}Si subes un PDF con el mismo nombre, se guarda como versión nueva.
      </p>

      <div className="fila">
        <label>Ámbito:
          <select value={curso} onChange={(e) => setCurso(e.target.value)} disabled={sinAmbito}>
            {esCoord && <option value="">Reglamentos generales</option>}
            {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="subir">
          <input type="file" accept="application/pdf" onChange={subir} disabled={sinAmbito} />
          <span>Subir PDF</span>
        </label>
      </div>

      <h4>Documentos actuales ({docs.length})</h4>
      {docs.length === 0
        ? <p className="vacio">Aún no hay documentos en este ámbito.</p>
        : <ul className="doc-lista">
            {docs.map((d) => (
              <li key={d.id} className={d.activo ? "" : "doc-inactivo"}>
                <div className="doc-fila">
                  <span>
                    {d.nombre} · v{d.version} · {d.fragmentos} fragmentos · {d.subido_en}
                    {!d.activo && <em className="chip-inactivo"> desactivado</em>}
                  </span>
                  <div className="doc-acciones">
                    <button className="btn-secundario" onClick={() => verVersiones(d)}>
                      Versiones ({d.versiones})
                    </button>
                    <button className="btn-secundario" onClick={() => cambiarEstado(d)}>
                      {d.activo ? "Desactivar" : "Activar"}
                    </button>
                    <button onClick={() => borrar(d)}>Quitar</button>
                  </div>
                </div>
                {versiones[d.id] && (
                  <ul className="doc-versiones">
                    {versiones[d.id].map((v) => (
                      <li key={v.numero}>
                        v{v.numero} · {v.subido_en} · {v.subido_por}
                        {v.restaurada_de && ` · restaurada desde v${v.restaurada_de}`}
                        {v.numero === d.version
                          ? <b> · vigente</b>
                          : <button className="btn-mini" onClick={() => restaurar(d, v.numero)}>
                              Restaurar
                            </button>}
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>}
    </section>
  );
}
