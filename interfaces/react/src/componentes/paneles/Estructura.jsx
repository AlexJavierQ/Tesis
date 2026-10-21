import { useEffect, useState } from "react";
import { BookOpen, Landmark, Plus, UserPlus, Check, X, GraduationCap } from "lucide-react";
import { api } from "../../api";
import { Encabezado, Tarjeta, Insignia, Vacio } from "../ui";

/**
 * Estructura academica (solo coordinacion): de facultad hacia abajo.
 *  - cursos de la carrera activa y los docentes asignados a cada uno
 *  - facultades y carreras
 */
export default function Estructura({ carrera, avisar, fallar, refrescarUsuario }) {
  const [facultades, setFacultades] = useState([]);
  const [cursos, setCursos] = useState([]);
  const [docentesCarrera, setDocentesCarrera] = useState([]);  // docentes de esta carrera
  const [asignados, setAsignados] = useState({});              // curso -> [usuarios]
  const [editando, setEditando] = useState(null);              // curso cuyo equipo se edita
  const [borrador, setBorrador] = useState([]);                // seleccion mientras se edita
  const [nuevoCurso, setNuevoCurso] = useState("");
  const [nuevaFacultad, setNuevaFacultad] = useState("");
  const [nuevaCarrera, setNuevaCarrera] = useState({ nombre: "", facultad: "" });

  useEffect(() => { cargar(); }, [carrera]);

  async function cargar() {
    try {
      const fs = await api.facultades();
      setFacultades(fs);
      setNuevaCarrera((n) => ({ ...n, facultad: n.facultad || fs[0]?.nombre || "" }));
      const cs = await api.cursos(carrera);
      setCursos(cs);
      const usuarios = await api.usuarios.listar();
      setDocentesCarrera(usuarios.filter((u) => u.rol === "docente" && u.activo && u.carreras.includes(carrera)));
      const mapa = {};
      for (const c of cs) mapa[c] = await api.docentesCurso(carrera, c);
      setAsignados(mapa);
    } catch (e) { fallar(e.message); }
  }

  async function hacer(accion, mensaje) {
    try {
      await accion();
      avisar(mensaje);
      cargar();
      return true;
    } catch (e) { fallar(e.message); return false; }
  }

  function empezarEdicion(c) {
    setEditando(c);
    setBorrador(asignados[c] || []);
  }

  function marcar(usuario) {
    setBorrador((b) => (b.includes(usuario) ? b.filter((x) => x !== usuario) : [...b, usuario]));
  }

  async function guardarDocentes(c) {
    if (await hacer(() => api.asignarDocentes(carrera, c, borrador), `Docentes de "${c}" actualizados.`)) {
      setEditando(null);
    }
  }

  const facultadActual = facultades.find((f) => f.carreras.includes(carrera))?.nombre;

  return (
    <>
      <Encabezado contexto={facultadActual ? `Facultad de ${facultadActual}` : carrera}
                  titulo="Estructura académica"
                  descripcion="Crea los cursos de la carrera y asigna a los docentes que los dictan. Cada docente solo gestiona los documentos de sus cursos." />

      <Tarjeta titulo={`Cursos de ${carrera}`}
               descripcion={`${cursos.length} curso${cursos.length === 1 ? "" : "s"}`}
               acciones={
                 <form className="fila-acciones" onSubmit={(e) => {
                   e.preventDefault();
                   hacer(() => api.crearCurso(carrera, nuevoCurso.trim()),
                         `Curso "${nuevoCurso.trim()}" creado. Ahora asígnale docentes.`)
                     .then((ok) => ok && setNuevoCurso(""));
                 }}>
                   <input value={nuevoCurso} onChange={(e) => setNuevoCurso(e.target.value)}
                          placeholder="Nombre del nuevo curso" style={{ width: 240 }} />
                   <button className="btn btn-primario" disabled={!nuevoCurso.trim()}>
                     <Plus size={18} />Crear curso
                   </button>
                 </form>
               }>
        {cursos.length === 0
          ? <Vacio icono={BookOpen} titulo="Aún no hay cursos">Crea el primero con el formulario de arriba.</Vacio>
          : <ul className="filas">
              {cursos.map((c) => {
                const equipo = asignados[c] || [];
                return (
                  <li key={c}>
                    <div className="fila">
                      <div className="fila-icono"><BookOpen size={20} /></div>
                      <div className="fila-cuerpo">
                        <div className="fila-titulo">{c}</div>
                        <div className="fila-meta">
                          {equipo.length
                            ? equipo.map((d) => <Insignia key={d}>{d}</Insignia>)
                            : <Insignia tipo="aviso">Sin docentes asignados</Insignia>}
                        </div>
                      </div>
                      {editando !== c && (
                        <button className="btn btn-secundario btn-chico" onClick={() => empezarEdicion(c)}>
                          <UserPlus size={15} />Asignar docentes
                        </button>
                      )}
                    </div>

                    {editando === c && (
                      <div className="subpanel">
                        {docentesCarrera.length === 0
                          ? <p>No hay docentes activos en esta carrera. Créalos en la sección Usuarios.</p>
                          : <div className="casillas">
                              {docentesCarrera.map((d) => (
                                <label key={d.usuario} className="casilla">
                                  <input type="checkbox" checked={borrador.includes(d.usuario)}
                                         onChange={() => marcar(d.usuario)} />
                                  {d.nombre}
                                </label>
                              ))}
                            </div>}
                        <div className="fila-acciones derecha" style={{ marginTop: 16 }}>
                          <button className="btn btn-fantasma btn-chico" onClick={() => setEditando(null)}>
                            <X size={15} />Cancelar
                          </button>
                          <button className="btn btn-primario btn-chico" onClick={() => guardarDocentes(c)}>
                            <Check size={15} />Guardar
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>}
      </Tarjeta>

      <Tarjeta titulo="Facultades y carreras"
               descripcion="Las carreras que crees quedan asignadas a ti; elígelas abajo a la izquierda para gestionarlas.">
        <ul className="filas">
          {facultades.map((f) => (
            <li key={f.nombre} className="fila">
              <div className="fila-icono"><Landmark size={20} /></div>
              <div className="fila-cuerpo">
                <div className="fila-titulo">{f.nombre}</div>
                <div className="fila-meta">
                  {f.carreras.length
                    ? f.carreras.map((c) => <Insignia key={c} tipo={c === carrera ? "primario" : undefined}>
                        <GraduationCap size={12} />{c}</Insignia>)
                    : <span>Sin carreras</span>}
                </div>
              </div>
            </li>
          ))}
        </ul>

        <div className="rejilla-campos" style={{ marginTop: 24 }}>
          <form className="campo" onSubmit={(e) => {
            e.preventDefault();
            hacer(() => api.crearFacultad(nuevaFacultad.trim()), `Facultad "${nuevaFacultad.trim()}" creada.`)
              .then((ok) => ok && setNuevaFacultad(""));
          }}>
            <span>Nueva facultad</span>
            <div className="fila-acciones">
              <input value={nuevaFacultad} onChange={(e) => setNuevaFacultad(e.target.value)}
                     placeholder="Nombre de la facultad" style={{ flex: 1 }} />
              <button className="btn btn-secundario" disabled={!nuevaFacultad.trim()}>Crear</button>
            </div>
          </form>
          <form className="campo" onSubmit={(e) => {
            e.preventDefault();
            hacer(() => api.crearCarrera(nuevaCarrera.nombre.trim(), nuevaCarrera.facultad),
                  `Carrera "${nuevaCarrera.nombre.trim()}" creada y asignada a ti.`)
              .then((ok) => { if (ok) { setNuevaCarrera({ ...nuevaCarrera, nombre: "" }); refrescarUsuario(); } });
          }}>
            <span>Nueva carrera</span>
            <div className="fila-acciones">
              <input value={nuevaCarrera.nombre} placeholder="Nombre" style={{ flex: 1 }}
                     onChange={(e) => setNuevaCarrera({ ...nuevaCarrera, nombre: e.target.value })} />
              <select value={nuevaCarrera.facultad} style={{ width: 170 }} aria-label="Facultad"
                      onChange={(e) => setNuevaCarrera({ ...nuevaCarrera, facultad: e.target.value })}>
                {facultades.map((f) => <option key={f.nombre} value={f.nombre}>{f.nombre}</option>)}
              </select>
              <button className="btn btn-secundario" disabled={!nuevaCarrera.nombre.trim()}>Crear</button>
            </div>
          </form>
        </div>
      </Tarjeta>
    </>
  );
}
