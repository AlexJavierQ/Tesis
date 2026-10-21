import { useEffect, useState } from "react";
import { RotateCcw, Search, History } from "lucide-react";
import { api } from "../../api";
import { Encabezado, Tarjeta, Insignia, Segmentado, Vacio } from "../ui";

// cada accion de la bitacora: texto legible, categoria y color de la insignia
const ACCIONES = {
  login: ["Inicio de sesión", "sesiones", "exito"],
  login_fallido: ["Intento fallido de acceso", "sesiones", "peligro"],
  logout: ["Cierre de sesión", "sesiones"],
  crear_usuario: ["Usuario creado", "usuarios", "primario"],
  editar_usuario: ["Usuario modificado", "usuarios"],
  borrar_usuario: ["Usuario eliminado", "usuarios", "peligro"],
  subir_documento: ["Documento subido", "documentos", "primario"],
  restaurar_documento: ["Versión restaurada", "documentos", "aviso"],
  activar_documento: ["Documento activado", "documentos", "exito"],
  desactivar_documento: ["Documento desactivado", "documentos", "aviso"],
  borrar_documento: ["Documento eliminado", "documentos", "peligro"],
  crear_facultad: ["Facultad creada", "estructura", "primario"],
  crear_carrera: ["Carrera creada", "estructura", "primario"],
  crear_curso: ["Curso creado", "estructura", "primario"],
  asignar_docentes: ["Docentes asignados", "estructura"],
  cambiar_parametro: ["Configuración cambiada", "configuracion", "aviso"],
};

const FILTROS = [
  { valor: "todas", texto: "Todas" },
  { valor: "sesiones", texto: "Sesiones" },
  { valor: "usuarios", texto: "Usuarios" },
  { valor: "documentos", texto: "Documentos" },
  { valor: "estructura", texto: "Estructura" },
  { valor: "configuracion", texto: "Configuración" },
];

/** Bitacora del sistema (solo administrador): quien hizo que y cuando. */
export default function Registro({ fallar }) {
  const [logs, setLogs] = useState([]);
  const [categoria, setCategoria] = useState("todas");
  const [busqueda, setBusqueda] = useState("");

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try { setLogs(await api.logs()); }
    catch (e) { fallar(e.message); }
  }

  const texto = busqueda.trim().toLowerCase();
  const visibles = logs.filter((l) => {
    const cat = ACCIONES[l.accion]?.[1];
    return (categoria === "todas" || cat === categoria)
      && (!texto || `${l.usuario} ${l.detalle}`.toLowerCase().includes(texto));
  });

  return (
    <>
      <Encabezado contexto="Sistema" titulo="Registro de actividad"
                  descripcion="Quién hizo qué y cuándo: accesos, cambios de usuarios, de estructura, de documentos y de configuración.">
        <button className="btn btn-secundario" onClick={cargar}><RotateCcw size={16} />Actualizar</button>
      </Encabezado>

      <Tarjeta>
        <div className="herramientas">
          <div className="buscador">
            <Search size={17} />
            <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
                   placeholder="Buscar por usuario o detalle" />
          </div>
          <Segmentado opciones={FILTROS} valor={categoria} onChange={setCategoria} />
        </div>

        {visibles.length === 0
          ? <Vacio icono={History} titulo="No hay actividad que coincida" />
          : <div className="tabla-envoltura">
              <table className="tabla">
                <thead>
                  <tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Detalle</th></tr>
                </thead>
                <tbody>
                  {visibles.map((l, i) => {
                    const [nombre, , tipo] = ACCIONES[l.accion] || [l.accion];
                    return (
                      <tr key={i}>
                        <td className="secundario" style={{ whiteSpace: "nowrap" }}>{l.fecha}</td>
                        <td><strong>{l.usuario}</strong></td>
                        <td><Insignia tipo={tipo}>{nombre}</Insignia></td>
                        <td className="secundario">{l.detalle || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>}
      </Tarjeta>
    </>
  );
}
