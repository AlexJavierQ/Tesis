import { useEffect, useState } from "react";
import { BookOpen, Plus, UserPlus, Check, X } from "lucide-react";
import { api } from "../../api";
import { nombre, plural } from "../../formato";
import { Encabezado, Tarjeta, Insignia, Vacio, PanelFormulario } from "../ui";

/**
 * Cursos y docentes (solo coordinacion), por cada carrera que coordina:
 *  - crear cursos
 *  - asignar los docentes que dictan cada curso (cada docente solo gestiona
 *    los documentos de sus cursos)
 * Las facultades y carreras las crea el administrador.
 */
export default function Cursos({ usuario, avisar, fallar }) {
  const [porCarrera, setPorCarrera] = useState({});   // carrera -> {cursos, docentes, asignados}
  const [creando, setCreando] = useState(false);
  const [nuevo, setNuevo] = useState({ carrera: usuario.carreras[0], nombre: "", docentes: [] });
  const [editando, setEditando] = useState(null);     // "carrera|curso" en edicion
  const [borrador, setBorrador] = useState([]);

  useEffect(() => { cargar(); }, []);

  async function cargar() {
    try {
      const usuarios = await api.usuarios.listar();
      const datos = {};
      for (const c of usuario.carreras) {
        const cursos = await api.cursos(c);
        const asignados = {};
        for (const cu of cursos) asignados[cu] = await api.docentesCurso(c, cu);
        datos[c] = {
          cursos,
          asignados,
          docentes: usuarios.filter((u) => u.rol === "docente" && u.activo && u.carreras.includes(c)),
        };
      }
      setPorCarrera(datos);
    } catch (e) { fallar(e.message); }
  }

  function alternar(lista, valor) {
    return lista.includes(valor) ? lista.filter((x) => x !== valor) : [...lista, valor];
  }

  async function crearCurso() {
    const n = nuevo.nombre.trim();
    try {
      await api.crearCurso(nuevo.carrera, n);
      if (nuevo.docentes.length) await api.asignarDocentes(nuevo.carrera, n, nuevo.docentes);
      avisar(`Curso "${n}" creado en ${nombre(nuevo.carrera)}.`);
      setNuevo({ ...nuevo, nombre: "", docentes: [] });
      setCreando(false);
      cargar();
    } catch (e) { fallar(e.message); }
  }

  async function guardarDocentes(carrera, curso) {
    try {
      await api.asignarDocentes(carrera, curso, borrador);
      avisar(`Docentes de "${curso}" actualizados.`);
      setEditando(null);
      cargar();
    } catch (e) { fallar(e.message); }
  }

  const docentesNuevo = porCarrera[nuevo.carrera]?.docentes || [];

  return (
    <>
      <Encabezado titulo="Cursos y docentes"
                  descripcion="Crea los cursos de tus carreras y asigna a quién los dicta. Cada docente solo gestiona los documentos de sus cursos.">
        {!creando && (
          <button className="btn btn-primario" onClick={() => setCreando(true)}>
            <Plus size={18} />Nuevo curso
          </button>
        )}
      </Encabezado>

      {creando && (
        <PanelFormulario titulo="Nuevo curso"
                         descripcion="El curso queda disponible en el chat y en Documentos en cuanto lo crees."
                         textoEnviar="Crear curso" valido={Boolean(nuevo.nombre.trim())}
                         onCancelar={() => setCreando(false)} onEnviar={crearCurso}>
          <div className="rejilla-campos">
            <label className="campo">
              <span>Nombre del curso</span>
              <input value={nuevo.nombre} autoFocus placeholder="Por ejemplo, Prácticum 3"
                     onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} />
            </label>
            <label className="campo">
              <span>Carrera</span>
              <select value={nuevo.carrera} disabled={usuario.carreras.length === 1}
                      onChange={(e) => setNuevo({ ...nuevo, carrera: e.target.value, docentes: [] })}>
                {usuario.carreras.map((c) => <option key={c} value={c}>{nombre(c)}</option>)}
              </select>
            </label>
          </div>
          <div className="campo" style={{ marginTop: 22 }}>
            <span>Docentes que lo dictan</span>
            {docentesNuevo.length === 0
              ? <small>No hay docentes activos en esta carrera. Puedes asignarlos después.</small>
              : <div className="casillas">
                  {docentesNuevo.map((d) => (
                    <label key={d.usuario} className="casilla">
                      <input type="checkbox" checked={nuevo.docentes.includes(d.usuario)}
                             onChange={() => setNuevo({ ...nuevo, docentes: alternar(nuevo.docentes, d.usuario) })} />
                      {d.nombre}
                    </label>
                  ))}
                </div>}
            <small>Opcional. Puedes cambiarlos cuando quieras.</small>
          </div>
        </PanelFormulario>
      )}

      <div className="pila">
        {usuario.carreras.map((c) => {
          const datos = porCarrera[c];
          if (!datos) return null;
          return (
            <Tarjeta key={c} titulo={nombre(c)} descripcion={plural(datos.cursos.length, "curso")}>
              {datos.cursos.length === 0
                ? <Vacio icono={BookOpen} titulo="Esta carrera aún no tiene cursos">
                    Usa «Nuevo curso» para crear el primero.
                  </Vacio>
                : <ul className="filas">
                    {datos.cursos.map((cu) => {
                      const clave = `${c}|${cu}`;
                      const equipo = datos.asignados[cu] || [];
                      const nombreDe = (u) => datos.docentes.find((d) => d.usuario === u)?.nombre || u;
                      return (
                        <li key={cu}>
                          <div className="fila">
                            <div className="fila-icono"><BookOpen size={20} /></div>
                            <div className="fila-cuerpo">
                              <div className="fila-titulo">{cu}</div>
                              <div className="fila-meta">
                                {equipo.length
                                  ? equipo.map((u) => <Insignia key={u}>{nombreDe(u)}</Insignia>)
                                  : <Insignia tipo="aviso">Sin docentes asignados</Insignia>}
                              </div>
                            </div>
                            {editando !== clave && (
                              <button className="btn btn-secundario btn-chico"
                                      onClick={() => { setEditando(clave); setBorrador(equipo); }}>
                                <UserPlus size={15} />Asignar docentes
                              </button>
                            )}
                          </div>

                          {editando === clave && (
                            <div className="subpanel">
                              {datos.docentes.length === 0
                                ? <p>No hay docentes activos en esta carrera. Créalos en la sección Usuarios.</p>
                                : <div className="casillas">
                                    {datos.docentes.map((d) => (
                                      <label key={d.usuario} className="casilla">
                                        <input type="checkbox" checked={borrador.includes(d.usuario)}
                                               onChange={() => setBorrador(alternar(borrador, d.usuario))} />
                                        {d.nombre}
                                      </label>
                                    ))}
                                  </div>}
                              <div className="fila-acciones derecha" style={{ marginTop: 16 }}>
                                <button className="btn btn-fantasma btn-chico" onClick={() => setEditando(null)}>
                                  <X size={15} />Cancelar
                                </button>
                                <button className="btn btn-primario btn-chico" onClick={() => guardarDocentes(c, cu)}>
                                  <Check size={15} />Guardar docentes
                                </button>
                              </div>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>}
            </Tarjeta>
          );
        })}
      </div>
    </>
  );
}
