import { useEffect } from "react";
import { CircleCheck, CircleX, X } from "lucide-react";

/**
 * Piezas visuales que se repiten en todas las pantallas. Asi cada panel
 * solo describe SU contenido y el aspecto queda igual en toda la app.
 */

/** Titulo de la pagina, con descripcion y botones a la derecha. */
export function Encabezado({ contexto, titulo, descripcion, children }) {
  return (
    <header className="encabezado">
      <div>
        {contexto && <div className="encabezado-contexto">{contexto}</div>}
        <h1>{titulo}</h1>
        {descripcion && <p>{descripcion}</p>}
      </div>
      {children && <div className="fila-acciones">{children}</div>}
    </header>
  );
}

/** Caja blanca con titulo opcional. */
export function Tarjeta({ titulo, descripcion, acciones, children, className = "" }) {
  return (
    <section className={"tarjeta " + className}>
      {(titulo || acciones) && (
        <div className="tarjeta-cabecera">
          <div>
            {titulo && <h2>{titulo}</h2>}
            {descripcion && <p>{descripcion}</p>}
          </div>
          {acciones && <div className="fila-acciones">{acciones}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

/** Etiqueta de color. tipo: primario | exito | peligro | aviso | (neutro). */
export function Insignia({ tipo, children }) {
  return <span className={"insignia" + (tipo ? " insignia-" + tipo : "")}>{children}</span>;
}

/** Mensaje para cuando una lista esta vacia. */
export function Vacio({ icono: Icono, titulo, children }) {
  return (
    <div className="vacio">
      {Icono && <Icono size={36} strokeWidth={1.5} />}
      {titulo && <strong>{titulo}</strong>}
      {children && <span>{children}</span>}
    </div>
  );
}

/** Elegir una opcion entre pocas: [{valor, texto, icono, deshabilitado}]. */
export function Segmentado({ opciones, valor, onChange }) {
  return (
    <div className="segmentado" role="tablist">
      {opciones.map(({ valor: v, texto, icono: Icono, deshabilitado }) => (
        <button key={v} type="button" role="tab" aria-selected={v === valor}
                className={v === valor ? "activo" : ""} disabled={deshabilitado}
                onClick={() => onChange(v)}>
          {Icono && <Icono size={16} />}{texto}
        </button>
      ))}
    </div>
  );
}

/** Ventana emergente. Se cierra con la X, con Escape o haciendo clic fuera. */
export function Modal({ titulo, descripcion, onCerrar, children, pie }) {
  useEffect(() => {
    const alPresionar = (e) => e.key === "Escape" && onCerrar();
    window.addEventListener("keydown", alPresionar);
    return () => window.removeEventListener("keydown", alPresionar);
  }, [onCerrar]);

  return (
    <div className="modal-fondo" onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="modal-cabecera">
          <div>
            <h2>{titulo}</h2>
            {descripcion && <p>{descripcion}</p>}
          </div>
          <button className="btn btn-fantasma btn-icono" onClick={onCerrar} aria-label="Cerrar">
            <X size={18} />
          </button>
        </div>
        {children}
        {pie && <div className="modal-pie">{pie}</div>}
      </div>
    </div>
  );
}

/** Avisos flotantes (exito / error) que aparecen arriba a la derecha. */
export function Notificaciones({ lista, onCerrar }) {
  return (
    <div className="notificaciones" aria-live="polite">
      {lista.map((n) => (
        <div key={n.id} className={"notificacion " + n.tipo}>
          {n.tipo === "error" ? <CircleX size={18} /> : <CircleCheck size={18} />}
          <p>{n.texto}</p>
          <button onClick={() => onCerrar(n.id)} aria-label="Cerrar"><X size={16} /></button>
        </div>
      ))}
    </div>
  );
}
