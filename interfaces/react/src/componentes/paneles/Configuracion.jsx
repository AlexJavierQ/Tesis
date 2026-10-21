import { useEffect, useState } from "react";
import { Search, Cpu, Brain, MessageSquare, Lock, ChartColumn, Save, Undo2, Info } from "lucide-react";
import { api } from "../../api";
import { Encabezado, Tarjeta } from "../ui";
import { fecha } from "../../formato";

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
      <Encabezado titulo="Configuración"
                  descripcion="Ajustes del asistente que antes estaban fijos en el código. La clave de acceso al modelo no se gestiona aquí: es un secreto y se guarda fuera de la base de datos." />

      <div className="con-indice">
        <nav className="indice" aria-label="Áreas de configuración">
          {areas.map((a) => {
            const Icono = ICONO_AREA[a.clave] || Info;
            return (
              <button key={a.clave} className={"indice-item" + (a.clave === areaActiva ? " activo" : "")}
                      aria-current={a.clave === areaActiva ? "true" : undefined}
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
              const esTextoLargo = p.clave.startsWith("mensaje_");
              return (
                <div key={p.clave} className={"parametro" + (esTextoLargo ? " parametro-ancho" : "")}>
                  <div>
                    <h3>{p.etiqueta}</h3>
                    <p className="descripcion">{p.descripcion}</p>
                    <dl>
                      {p.tipo !== "texto" && <div><dt>Rango</dt><dd>{p.minimo} a {p.maximo}</dd></div>}
                      {p.defecto.length <= 40 && <div><dt>Por defecto</dt><dd>{p.defecto}</dd></div>}
                      <div>
                        <dt>Último cambio</dt>
                        <dd>{fecha(p.actualizado_en)}{p.actualizado_por !== "—" && `, por ${p.actualizado_por}`}</dd>
                      </div>
                    </dl>
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
