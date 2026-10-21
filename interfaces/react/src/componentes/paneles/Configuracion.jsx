import { useEffect, useState } from "react";
import { Search, Cpu, Brain, MessageSquare, Lock, ChartColumn, Save, Undo2, Info } from "lucide-react";
import { api } from "../../api";
import { Encabezado, Tarjeta } from "../ui";

// icono de cada area (las areas y sus parametros los define el backend)
const ICONO_AREA = {
  busqueda: Search, modelo: Cpu, memoria: Brain,
  mensajes: MessageSquare, acceso: Lock, metricas: ChartColumn,
};

/**
 * Configuracion del sistema (solo administrador), separada por areas.
 * A la izquierda se elige el area; a la derecha se editan sus parametros.
 * La API valida tipo y rango; cada cambio queda en el Registro de actividad
 * y se aplica desde la siguiente pregunta, sin reiniciar el servidor.
 */
export default function Configuracion({ avisar, fallar }) {
  const [areas, setAreas] = useState([]);
  const [areaActiva, setAreaActiva] = useState(null);
  const [borrador, setBorrador] = useState({});   // clave -> valor que se esta editando

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try {
      const datos = await api.parametros();
      setAreas(datos);
      setAreaActiva((a) => a || datos[0]?.clave);
      const valores = {};
      datos.forEach((a) => a.parametros.forEach((p) => { valores[p.clave] = p.valor; }));
      setBorrador(valores);
    } catch (e) { fallar(e.message); }
  }

  async function guardar(p, valor) {
    try {
      await api.cambiarParametro(p.clave, valor);
      avisar(`"${p.etiqueta}" actualizado. Se aplica desde la próxima pregunta.`);
      cargar();
    } catch (e) { fallar(`${p.etiqueta}: ${e.message}`); }
  }

  const area = areas.find((a) => a.clave === areaActiva);

  return (
    <>
      <Encabezado contexto="Sistema" titulo="Configuración"
                  descripcion="Ajustes del asistente que antes estaban fijos en el código. La clave de acceso al modelo no se gestiona aquí: es un secreto y se guarda fuera de la base de datos." />

      <div className="config">
        <nav className="config-areas">
          {areas.map((a) => {
            const Icono = ICONO_AREA[a.clave] || Info;
            return (
              <button key={a.clave} className={"area-boton" + (a.clave === areaActiva ? " activo" : "")}
                      onClick={() => setAreaActiva(a.clave)}>
                <Icono size={18} />{a.titulo}
              </button>
            );
          })}
        </nav>

        {area && (
          <Tarjeta titulo={area.titulo} descripcion={area.descripcion}>
            {area.parametros.map((p) => {
              const cambiado = borrador[p.clave] !== p.valor;
              const esTextoLargo = p.tipo === "texto" && !p.opciones.length;
              return (
                <div key={p.clave} className={"parametro" + (esTextoLargo ? " parametro-ancho" : "")}>
                  <div>
                    <h3>{p.etiqueta}</h3>
                    <p className="descripcion">{p.descripcion}</p>
                    <p className="detalle">
                      {p.tipo !== "texto" && <>Rango permitido: {p.minimo} a {p.maximo} · </>}
                      Valor por defecto: {p.defecto.length > 40 ? "texto original" : p.defecto} ·
                      Último cambio: {p.actualizado_en.slice(0, 16)} ({p.actualizado_por})
                    </p>
                  </div>
                  <div className="parametro-control">
                    {p.opciones.length > 0
                      ? <select value={borrador[p.clave] ?? ""}
                                onChange={(e) => setBorrador({ ...borrador, [p.clave]: e.target.value })}>
                          {p.opciones.map((o) => <option key={o} value={o}>{o}</option>)}
                        </select>
                      : esTextoLargo
                      ? <textarea rows={3} value={borrador[p.clave] ?? ""}
                                  onChange={(e) => setBorrador({ ...borrador, [p.clave]: e.target.value })} />
                      : <input value={borrador[p.clave] ?? ""}
                               type={p.tipo === "texto" ? "text" : "number"}
                               step={p.tipo === "entero" ? 1 : 0.01} min={p.minimo ?? undefined} max={p.maximo ?? undefined}
                               onChange={(e) => setBorrador({ ...borrador, [p.clave]: e.target.value })} />}
                    <div className="fila-acciones">
                      <button className="btn btn-fantasma btn-chico" disabled={p.valor === p.defecto}
                              onClick={() => guardar(p, p.defecto)} title="Volver al valor por defecto">
                        <Undo2 size={15} />Por defecto
                      </button>
                      <button className="btn btn-primario btn-chico" disabled={!cambiado}
                              onClick={() => guardar(p, borrador[p.clave])}>
                        <Save size={15} />Guardar
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </Tarjeta>
        )}
      </div>
    </>
  );
}
