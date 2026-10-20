import { useEffect, useState } from "react";
import { api } from "../../api";

/**
 * Configuracion del sistema (solo administrador).
 * Muestra los parametros de la tabla `parametros` y permite cambiarlos sin
 * tocar el codigo. La API valida tipo y rango; cada cambio queda en el Registro.
 * El cambio se aplica desde la siguiente pregunta, sin reiniciar el servidor.
 */
export default function Configuracion({ avisar, fallar }) {
  const [parametros, setParametros] = useState([]);
  const [borrador, setBorrador] = useState({});   // clave -> valor que se esta editando

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try {
      const ps = await api.parametros();
      setParametros(ps);
      setBorrador(Object.fromEntries(ps.map((p) => [p.clave, p.valor])));
    } catch (e) { fallar(e.message); }
  }

  async function guardar(clave, valor) {
    try {
      await api.cambiarParametro(clave, valor);
      avisar(`"${clave}" actualizado. Se aplica desde la próxima pregunta.`);
      cargar();
    } catch (e) { fallar(`${clave}: ${e.message}`); }
  }

  return (
    <section className="admin-seccion">
      <h3>Configuración del sistema</h3>
      <p className="admin-nota">
        Valores que antes estaban fijos en el código. La clave de acceso al
        modelo (API key) no se gestiona aquí: es un secreto y vive fuera de la
        base de datos.
      </p>

      <table className="tabla-usuarios tabla-config">
        <thead>
          <tr><th>Parámetro</th><th>Valor</th><th>Último cambio</th><th></th></tr>
        </thead>
        <tbody>
          {parametros.map((p) => {
            const cambiado = borrador[p.clave] !== p.valor;
            return (
              <tr key={p.clave}>
                <td>
                  <b>{p.clave}</b>
                  <br /><small>{p.descripcion}</small>
                  {p.tipo !== "texto" && <br />}
                  {p.tipo !== "texto" && <small>Rango: {p.minimo} – {p.maximo}</small>}
                </td>
                <td>
                  {p.opciones?.length > 0
                    ? <select value={borrador[p.clave] ?? ""}
                              onChange={(e) => setBorrador({ ...borrador, [p.clave]: e.target.value })}>
                        {p.opciones.map((o) => <option key={o} value={o}>{o}</option>)}
                      </select>
                    : p.tipo === "texto"
                    ? <textarea rows={3} value={borrador[p.clave] ?? ""}
                                onChange={(e) => setBorrador({ ...borrador, [p.clave]: e.target.value })} />
                    : <input type="number" value={borrador[p.clave] ?? ""}
                             step={p.tipo === "entero" ? 1 : 0.01} min={p.minimo} max={p.maximo}
                             onChange={(e) => setBorrador({ ...borrador, [p.clave]: e.target.value })} />}
                </td>
                <td><small>{p.actualizado_en}<br />{p.actualizado_por}</small></td>
                <td>
                  <button disabled={!cambiado} onClick={() => guardar(p.clave, borrador[p.clave])}>
                    Guardar
                  </button>
                  <button className="btn-secundario" disabled={p.valor === p.defecto}
                          onClick={() => guardar(p.clave, p.defecto)}>
                    Por defecto
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
