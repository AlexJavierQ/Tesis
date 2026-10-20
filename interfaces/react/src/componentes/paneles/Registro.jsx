import { useEffect, useState } from "react";
import { api } from "../../api";

/** Bitacora del sistema (solo administrador): quien hizo que y cuando. */
export default function Registro({ fallar }) {
  const [logs, setLogs] = useState([]);

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try { setLogs(await api.logs()); }
    catch (e) { fallar(e.message); }
  }

  return (
    <section className="admin-seccion">
      <h3>Registro de actividad</h3>
      <p className="admin-nota">
        Inicios de sesión (también los fallidos), cambios de usuarios, de
        estructura, de documentos y de configuración.
      </p>
      <button onClick={cargar}>🔄 Actualizar</button>
      {logs.length === 0
        ? <p className="vacio">Sin actividad registrada.</p>
        : <table className="tabla-usuarios">
            <thead>
              <tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalle</th></tr>
            </thead>
            <tbody>
              {logs.map((l, i) => (
                <tr key={i}>
                  <td>{l.fecha}</td><td>{l.usuario}</td><td>{l.accion}</td><td>{l.detalle}</td>
                </tr>
              ))}
            </tbody>
          </table>}
    </section>
  );
}
