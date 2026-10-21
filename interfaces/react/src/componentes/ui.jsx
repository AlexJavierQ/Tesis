import { CircleCheck, CircleX, X } from "lucide-react";

/**
 * Piezas visuales que se repiten en todas las pantallas. Asi cada panel
 * solo describe SU contenido y el aspecto queda igual en toda la app.
 */

/** Titulo de la pagina, con descripcion y botones a la derecha. */
export function Encabezado({ titulo, descripcion, children }) {
  return (
    <header className="encabezado">
      <div>
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

/**
 * Formulario que se despliega dentro de la pagina (en vez de una ventana
 * emergente): da espacio a los campos y no tapa el contexto.
 */
export function PanelFormulario({ titulo, descripcion, onCancelar, onEnviar, textoEnviar, valido, children }) {
  return (
    <form className="panel-formulario"
          onSubmit={(e) => { e.preventDefault(); if (valido) onEnviar(); }}
          onKeyDown={(e) => e.key === "Escape" && onCancelar()}>
      <h2>{titulo}</h2>
      {descripcion && <p>{descripcion}</p>}
      {children}
      <div className="pie">
        <button type="button" className="btn btn-fantasma" onClick={onCancelar}>Cancelar</button>
        <button type="submit" className="btn btn-primario" disabled={!valido}>{textoEnviar}</button>
      </div>
    </form>
  );
}

/** Etiqueta de color. tipo: primario | exito | peligro | aviso | (neutro). */
export function Insignia({ tipo, children }) {
  return <span className={"insignia" + (tipo ? " insignia-" + tipo : "")}>{children}</span>;
}

/** Mensaje para cuando una lista esta vacia: dice que pasa y que hacer. */
export function Vacio({ icono: Icono, titulo, children }) {
  return (
    <div className="vacio">
      {Icono && <Icono size={36} strokeWidth={1.5} />}
      {titulo && <strong>{titulo}</strong>}
      {children && <span>{children}</span>}
    </div>
  );
}

/** Elegir una opcion entre pocas (filtros): [{valor, texto}]. */
export function Segmentado({ opciones, valor, onChange, etiqueta }) {
  return (
    <div className="segmentado" role="radiogroup" aria-label={etiqueta}>
      {opciones.map(({ valor: v, texto }) => (
        <button key={v} type="button" role="radio" aria-checked={v === valor}
                className={v === valor ? "activo" : ""} onClick={() => onChange(v)}>
          {texto}
        </button>
      ))}
    </div>
  );
}

/** Avisos flotantes (exito / error) que aparecen arriba a la derecha. */
export function Notificaciones({ lista, onCerrar }) {
  return (
    <div className="notificaciones" aria-live="polite">
      {lista.map((n) => (
        <div key={n.id} className={"notificacion " + n.tipo} role={n.tipo === "error" ? "alert" : "status"}>
          {n.tipo === "error" ? <CircleX size={18} /> : <CircleCheck size={18} />}
          <p>{n.texto}</p>
          <button onClick={() => onCerrar(n.id)} aria-label="Cerrar aviso"><X size={16} /></button>
        </div>
      ))}
    </div>
  );
}
