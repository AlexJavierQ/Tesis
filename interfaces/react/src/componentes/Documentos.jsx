import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import Icono from "./Icono";

export default function Documentos({ carrera, curso, alVerDoc }) {
  const [docs, setDocs] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [subiendo, setSubiendo] = useState(false);
  const [aviso, setAviso] = useState(null);
  const [error, setError] = useState(null);
  const [arrastrando, setArrastrando] = useState(false);
  const inputRef = useRef(null);

  async function recargar() {
    setCargando(true);
    try {
      setDocs(await api.documentos(carrera, curso));
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }
  useEffect(() => { recargar(); }, [carrera, curso]);

  async function subir(archivo) {
    if (!archivo) return;
    if (!archivo.name.toLowerCase().endsWith(".pdf")) {
      setError("Solo acepto archivos PDF.");
      return;
    }
    setSubiendo(true); setAviso(null); setError(null);
    try {
      const r = await api.subirDocumento(carrera, curso, archivo);
      setAviso(`"${r.archivo}" listo. ${r.fragmentos} fragmentos indexados.`);
      await recargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubiendo(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function borrar(nombre) {
    if (!confirm(`¿Quitar "${nombre}"? Dejará de usarse en las respuestas.`)) return;
    try { await api.borrarDocumento(carrera, curso, nombre); await recargar(); }
    catch (e) { setError(e.message); }
  }

  return (
    <div className="doc-panel">
      <div
        className={`soltar${arrastrando ? " activo" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setArrastrando(true); }}
        onDragLeave={() => setArrastrando(false)}
        onDrop={(e) => { e.preventDefault(); setArrastrando(false); subir(e.dataTransfer.files?.[0]); }}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept="application/pdf" hidden
          onChange={(e) => subir(e.target.files?.[0])} />
        <Icono name="subir" size={22} className="soltar-icono" />
        {subiendo
          ? <span>Indexando…</span>
          : <span>Arrastra un PDF aquí o <b>haz clic para elegirlo</b></span>}
      </div>

      {aviso && <div className="aviso-ok">{aviso}</div>}
      {error && <div className="aviso-error">{error}</div>}

      {cargando ? (
        <p className="vacio">Cargando…</p>
      ) : docs.length === 0 ? (
        <p className="vacio">Aún no hay documentos aquí. Sube el primero.</p>
      ) : (
        <ul className="doc-lista">
          {docs.map((d) => (
            <li key={d.ref}>
              <Icono name="archivo" size={18} className="doc-ico" />
              <span className="doc-nom">{d.nombre.replace(/\.pdf$/i, "")}</span>
              <span className="doc-pag">{d.paginas} pág.</span>
              <button className="mini" onClick={() => alVerDoc({ ref: d.ref, fuente: d.nombre, pagina: 1 })}>Ver</button>
              <button className="mini peligro" onClick={() => borrar(d.nombre)}>Quitar</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
