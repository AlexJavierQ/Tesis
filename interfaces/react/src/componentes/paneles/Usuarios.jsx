import { useEffect, useState } from "react";
import { UserPlus, Search, KeyRound, Trash2, Users } from "lucide-react";
import { api } from "../../api";
import { NOMBRE_ROL } from "../../navegacion";
import { Encabezado, Tarjeta, Insignia, Segmentado, Modal, Vacio } from "../ui";

/**
 * Gestion de usuarios.
 *  - administrador: todos los usuarios, cualquier rol y carrera.
 *  - coordinacion: solo estudiantes y docentes de SUS carreras.
 * (La API aplica las mismas reglas; aqui solo se muestran las opciones validas.)
 */
export default function Usuarios({ usuario, carrera, avisar, fallar }) {
  const esAdmin = usuario.rol === "administrador";
  const rolesPermitidos = esAdmin
    ? ["estudiante", "docente", "coordinacion", "administrador"]
    : ["estudiante", "docente"];

  const [usuarios, setUsuarios] = useState([]);
  const [carrerasPosibles, setCarrerasPosibles] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [filtroRol, setFiltroRol] = useState("todos");
  const [creando, setCreando] = useState(false);

  useEffect(() => {
    cargar();
    if (esAdmin) api.carreras().then(setCarrerasPosibles).catch(() => {});
    else setCarrerasPosibles(usuario.carreras);
  }, []);

  async function cargar() {
    try { setUsuarios(await api.usuarios.listar()); }
    catch (e) { fallar(e.message); }
  }

  // envuelve una accion: si sale bien avisa y recarga; si falla muestra el error
  async function hacer(accion, mensaje) {
    try {
      await accion();
      avisar(mensaje);
      cargar();
      return true;
    } catch (e) { fallar(e.message); return false; }
  }

  function cambiarRol(u, rol) {
    if (u.rol === rol || !confirm(`¿Cambiar el rol de ${u.nombre} a ${NOMBRE_ROL[rol]}?`)) return;
    hacer(() => api.usuarios.actualizar(u.usuario, { rol }), `Rol de ${u.nombre} actualizado.`);
  }

  function cambiarPassword(u) {
    const p = prompt(`Nueva contraseña para ${u.nombre} (mínimo 6 caracteres):`);
    if (!p || !p.trim()) return;
    hacer(() => api.usuarios.actualizar(u.usuario, { nuevo_password: p }),
          `Contraseña de ${u.nombre} cambiada. Sus sesiones abiertas se cerraron.`);
  }

  function borrar(u) {
    if (!confirm(`¿Eliminar a ${u.nombre}? Se borran también sus conversaciones. No se puede deshacer.`)) return;
    hacer(() => api.usuarios.borrar(u.usuario), `${u.nombre} eliminado.`);
  }

  const texto = busqueda.trim().toLowerCase();
  const visibles = usuarios.filter((u) =>
    (filtroRol === "todos" || u.rol === filtroRol)
    && (!texto || [u.usuario, u.nombre, u.correo].some((v) => v.toLowerCase().includes(texto))));

  const filtros = [{ valor: "todos", texto: "Todos" },
    ...rolesPermitidos.map((r) => ({ valor: r, texto: NOMBRE_ROL[r] }))];

  return (
    <>
      <Encabezado contexto={esAdmin ? "Sistema" : carrera} titulo="Usuarios"
                  descripcion={esAdmin
                    ? "Todas las cuentas de la plataforma, incluidos coordinadores y administradores."
                    : "Estudiantes y docentes de tus carreras."}>
        <button className="btn btn-primario" onClick={() => setCreando(true)}>
          <UserPlus size={18} />Nuevo usuario
        </button>
      </Encabezado>

      <Tarjeta>
        <div className="herramientas">
          <div className="buscador">
            <Search size={17} />
            <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
                   placeholder="Buscar por nombre, usuario o correo" />
          </div>
          <Segmentado opciones={filtros} valor={filtroRol} onChange={setFiltroRol} />
        </div>

        {visibles.length === 0
          ? <Vacio icono={Users} titulo="No hay usuarios que coincidan" />
          : <div className="tabla-envoltura">
              <table className="tabla">
                <thead>
                  <tr><th>Persona</th><th>Rol</th><th>Carreras</th><th>Estado</th><th></th></tr>
                </thead>
                <tbody>
                  {visibles.map((u) => {
                    const soyYo = u.usuario === usuario.usuario;
                    return (
                      <tr key={u.usuario}>
                        <td>
                          <strong>{u.nombre}</strong>{soyYo && <> <Insignia tipo="primario">Tú</Insignia></>}
                          <div className="secundario">{u.usuario} · {u.correo}</div>
                        </td>
                        <td>
                          <select value={u.rol} disabled={soyYo} aria-label="Rol"
                                  onChange={(e) => cambiarRol(u, e.target.value)}>
                            {(rolesPermitidos.includes(u.rol) ? rolesPermitidos : [u.rol]).map((r) =>
                              <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
                          </select>
                        </td>
                        <td>{u.carreras.length
                          ? <div className="fila-meta">{u.carreras.map((c) => <Insignia key={c}>{c}</Insignia>)}</div>
                          : <span className="secundario">—</span>}</td>
                        <td>
                          <button className="btn btn-fantasma btn-chico" disabled={soyYo}
                                  title={u.activo ? "Clic para desactivar" : "Clic para activar"}
                                  onClick={() => hacer(() => api.usuarios.actualizar(u.usuario, { activo: !u.activo }),
                                    `${u.nombre} ${u.activo ? "desactivado: ya no puede iniciar sesión" : "activado"}.`)}>
                            {u.activo ? <Insignia tipo="exito">Activo</Insignia> : <Insignia>Inactivo</Insignia>}
                          </button>
                        </td>
                        <td>
                          <div className="fila-acciones-derecha">
                            <button className="btn btn-fantasma btn-icono" title="Cambiar contraseña"
                                    onClick={() => cambiarPassword(u)}><KeyRound size={16} /></button>
                            <button className="btn btn-peligro btn-icono" title="Eliminar usuario"
                                    disabled={soyYo} onClick={() => borrar(u)}><Trash2 size={16} /></button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>}
      </Tarjeta>

      {creando && (
        <NuevoUsuario roles={rolesPermitidos} carreras={carrerasPosibles} carreraInicial={carrera}
                      onCerrar={() => setCreando(false)}
                      onCrear={async (datos) => {
                        const ok = await hacer(() => api.usuarios.crear(datos), `${datos.nombre} fue creado.`);
                        if (ok) setCreando(false);
                      }} />
      )}
    </>
  );
}

/** Formulario de alta, en una ventana aparte para no saturar la pantalla. */
function NuevoUsuario({ roles, carreras, carreraInicial, onCerrar, onCrear }) {
  const [d, setD] = useState({
    usuario: "", nombre: "", correo: "", password: "",
    rol: "estudiante", carreras: carreraInicial ? [carreraInicial] : [],
  });
  const cambiar = (campo) => (e) => setD({ ...d, [campo]: e.target.value });
  const necesitaCarrera = d.rol !== "administrador";
  const valido = d.usuario.trim() && d.nombre.trim() && d.correo.trim()
    && d.password.length >= 6 && (!necesitaCarrera || d.carreras.length > 0);

  function marcar(c) {
    setD({ ...d, carreras: d.carreras.includes(c) ? d.carreras.filter((x) => x !== c) : [...d.carreras, c] });
  }

  return (
    <Modal titulo="Nuevo usuario" descripcion="La persona podrá entrar con su usuario o su correo."
           onCerrar={onCerrar}
           pie={<>
             <button className="btn btn-fantasma" onClick={onCerrar}>Cancelar</button>
             <button className="btn btn-primario" disabled={!valido} onClick={() => onCrear(d)}>
               <UserPlus size={18} />Crear usuario
             </button>
           </>}>
      <div className="rejilla-campos">
        <label className="campo"><span>Nombre completo</span>
          <input value={d.nombre} onChange={cambiar("nombre")} autoFocus /></label>
        <label className="campo"><span>Correo</span>
          <input type="email" value={d.correo} onChange={cambiar("correo")} placeholder="nombre@utpl.edu.ec" /></label>
        <label className="campo"><span>Usuario</span>
          <input value={d.usuario} onChange={cambiar("usuario")} placeholder="ej: jperez" /></label>
        <label className="campo"><span>Contraseña</span>
          <input type="password" value={d.password} onChange={cambiar("password")} />
          <small>Mínimo 6 caracteres.</small></label>
        <label className="campo"><span>Rol</span>
          <select value={d.rol} onChange={cambiar("rol")}>
            {roles.map((r) => <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
          </select></label>
      </div>
      <div className="campo" style={{ marginTop: 20 }}>
        <span>Carreras{necesitaCarrera ? "" : " (opcional para administradores)"}</span>
        <div className="casillas">
          {carreras.map((c) => (
            <label key={c} className="casilla">
              <input type="checkbox" checked={d.carreras.includes(c)} onChange={() => marcar(c)} />{c}
            </label>
          ))}
        </div>
      </div>
    </Modal>
  );
}
