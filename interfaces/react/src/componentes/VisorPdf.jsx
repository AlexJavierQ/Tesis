import { useEffect, useState } from "react";
import { api } from "../api";
import Icono from "./Icono";

/**
 * Visor modal que abre un PDF en la pagina exacta de la cita.
 * Es la pieza que hace verificable la respuesta: el estudiante comprueba
 * la fuente sin salir de la conversacion.
 */
export default function VisorPdf({ doc, alCerrar }) {
  const [pagina, setPagina] = useState(doc.pagina || 1);
  const [total, setTotal] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    api
      .infoDocumento(doc.ref)
      .then((i) => setTotal(i.paginas))
      .catch(() => setTotal(null));
  }, [doc.ref]);

  // Cerrar con Escape y navegar con las flechas
  useEffect(() => {
    const alPulsar = (e) => {
      if (e.key === "Escape") alCerrar();
      if (e.key === "ArrowLeft") setPagina((p) => Math.max(1, p - 1));
      if (e.key === "ArrowRight") setPagina((p) => (total ? Math.min(total, p + 1) : p + 1));
    };
    window.addEventListener("keydown", alPulsar);
    return () => window.removeEventListener("keydown", alPulsar);
  }, [alCerrar, total]);

  useEffect(() => setCargando(true), [pagina]);

  return (
    <div className="visor-fondo" onClick={alCerrar}>
      <div className="visor" onClick={(e) => e.stopPropagation()}>
        <header className="visor-cab">
          <div>
            <strong>{doc.fuente}</strong>
            <span className="visor-pag">
              pág. {pagina}
              {total ? ` / ${total}` : ""}
            </span>
          </div>
          <button className="btn-icono" onClick={alCerrar} aria-label="Cerrar">
            <Icono name="cerrar" size={18} />
          </button>
        </header>

        <div className="visor-cuerpo">
          {cargando && <div className="visor-cargando">Cargando página…</div>}
          <img
            src={api.urlPagina(doc.ref, pagina)}
            alt={`${doc.fuente}, página ${pagina}`}
            onLoad={() => setCargando(false)}
            onError={() => setCargando(false)}
            style={{ display: cargando ? "none" : "block" }}
          />
        </div>

        <footer className="visor-pie">
          <button onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina <= 1}>
            <Icono name="izquierda" size={16} /> Anterior
          </button>
          <span className="visor-ayuda">Usa ← → para navegar · Esc para cerrar</span>
          <button
            onClick={() => setPagina((p) => (total ? Math.min(total, p + 1) : p + 1))}
            disabled={total !== null && pagina >= total}
          >
            Siguiente <Icono name="derecha" size={16} />
          </button>
        </footer>
      </div>
    </div>
  );
}
