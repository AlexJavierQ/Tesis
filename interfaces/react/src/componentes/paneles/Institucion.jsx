import { useEffect, useState } from "react";
import { Landmark, GraduationCap, Plus } from "lucide-react";
import { api } from "../../api";
import { nombre, plural } from "../../formato";
import { Encabezado, Tarjeta, Insignia, Vacio, PanelFormulario } from "../ui";

/**
 * Facultades y carreras (solo administrador): la estructura institucional.
 * Cada carrera muestra quien la coordina y cuantos cursos tiene. Para asignar
 * un coordinador a una carrera se edita el usuario en la seccion Usuarios.
 */
export default function Institucion({ avisar, fallar }) {
  const [facultades, setFacultades] = useState([]);
  const [coordinadores, setCoordinadores] = useState({});  // carrera -> [nombres]
  const [cursos, setCursos] = useState({});                // carrera -> n cursos
  const [formulario, setFormulario] = useState(null);      // null | "facultad" | "carrera"
  const [nuevaFacultad, setNuevaFacultad] = useState("");
  const [nuevaCarrera, setNuevaCarrera] = useState({ nombre: "", facultad: "" });

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try {
      const fs = await api.facultades();
      setFacultades(fs);
      setNuevaCarrera((n) => ({ ...n, facultad: n.facultad || fs[0]?.nombre || "" }));
      const usuarios = await api.usuarios.listar();
      const coord = {};
      const nCursos = {};
      for (const f of fs) {
        for (const c of f.carreras) {
          coord[c] = usuarios.filter((u) => u.rol === "coordinacion" && u.carreras.includes(c)).map((u) => u.nombre);
          nCursos[c] = (await api.cursos(c)).length;
        }
      }
      setCoordinadores(coord);
      setCursos(nCursos);
    } catch (e) { fallar(e.message); }
  }

  async function crearFacultad() {
    try {
      await api.crearFacultad(nuevaFacultad.trim());
      avisar(`Facultad "${nuevaFacultad.trim()}" creada.`);
      setNuevaFacultad("");
      setFormulario(null);
      cargar();
    } catch (e) { fallar(e.message); }
  }

  async function crearCarrera() {
    try {
      await api.crearCarrera(nuevaCarrera.nombre.trim(), nuevaCarrera.facultad);
      avisar(`Carrera "${nuevaCarrera.nombre.trim()}" creada. Asígnale un coordinador en Usuarios.`);
      setNuevaCarrera({ ...nuevaCarrera, nombre: "" });
      setFormulario(null);
      cargar();
    } catch (e) { fallar(e.message); }
  }

  return (
    <>
      <Encabezado titulo="Facultades y carreras"
                  descripcion="La estructura institucional. Para que alguien coordine una carrera, asígnale esa carrera en Usuarios.">
        {!formulario && (
          <>
            <button className="btn btn-secundario" onClick={() => setFormulario("facultad")}>
              <Plus size={18} />Nueva facultad
            </button>
            <button className="btn btn-primario" onClick={() => setFormulario("carrera")}
                    disabled={facultades.length === 0}>
              <Plus size={18} />Nueva carrera
            </button>
          </>
        )}
      </Encabezado>

      {formulario === "facultad" && (
        <PanelFormulario titulo="Nueva facultad" textoEnviar="Crear facultad"
                         descripcion="Después podrás crear carreras dentro de ella."
                         valido={Boolean(nuevaFacultad.trim())}
                         onCancelar={() => setFormulario(null)} onEnviar={crearFacultad}>
          <label className="campo" style={{ maxWidth: 480 }}>
            <span>Nombre de la facultad</span>
            <input value={nuevaFacultad} autoFocus placeholder="Por ejemplo, Ciencias de la Salud"
                   onChange={(e) => setNuevaFacultad(e.target.value)} />
          </label>
        </PanelFormulario>
      )}

      {formulario === "carrera" && (
        <PanelFormulario titulo="Nueva carrera" textoEnviar="Crear carrera"
                         descripcion="La carrera empieza sin cursos ni documentos. Su coordinación los agregará."
                         valido={Boolean(nuevaCarrera.nombre.trim() && nuevaCarrera.facultad)}
                         onCancelar={() => setFormulario(null)} onEnviar={crearCarrera}>
          <div className="rejilla-campos">
            <label className="campo">
              <span>Nombre de la carrera</span>
              <input value={nuevaCarrera.nombre} autoFocus placeholder="Por ejemplo, telecomunicaciones"
                     onChange={(e) => setNuevaCarrera({ ...nuevaCarrera, nombre: e.target.value })} />
              <small>Sin barras ni símbolos especiales.</small>
            </label>
            <label className="campo">
              <span>Facultad</span>
              <select value={nuevaCarrera.facultad}
                      onChange={(e) => setNuevaCarrera({ ...nuevaCarrera, facultad: e.target.value })}>
                {facultades.map((f) => <option key={f.nombre} value={f.nombre}>{f.nombre}</option>)}
              </select>
            </label>
          </div>
        </PanelFormulario>
      )}

      {facultades.length === 0
        ? <Tarjeta><Vacio icono={Landmark} titulo="Aún no hay facultades">Crea la primera con «Nueva facultad».</Vacio></Tarjeta>
        : <div className="pila">
            {facultades.map((f) => (
              <Tarjeta key={f.nombre} titulo={f.nombre} descripcion={plural(f.carreras.length, "carrera")}>
                {f.carreras.length === 0
                  ? <Vacio icono={GraduationCap} titulo="Sin carreras">Usa «Nueva carrera» para agregar una.</Vacio>
                  : <ul className="filas">
                      {f.carreras.map((c) => (
                        <li key={c} className="fila">
                          <div className="fila-icono"><GraduationCap size={20} /></div>
                          <div className="fila-cuerpo">
                            <div className="fila-titulo">{nombre(c)}</div>
                            <div className="fila-meta">
                              <span>{plural(cursos[c] ?? 0, "curso")}</span>
                            </div>
                          </div>
                          {coordinadores[c]?.length
                            ? <span className="fila-meta">Coordina: {coordinadores[c].join(", ")}</span>
                            : <Insignia tipo="aviso">Sin coordinador</Insignia>}
                        </li>
                      ))}
                    </ul>}
              </Tarjeta>
            ))}
          </div>}
    </>
  );
}
