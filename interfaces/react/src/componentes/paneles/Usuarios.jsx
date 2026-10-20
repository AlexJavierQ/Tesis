import { useEffect, useState } from "react";
import { api } from "../../api";

const NOMBRE_ROL = {
  estudiante: "Estudiante",
  docente: "Docente",
  coordinacion: "Coordinación",
  administrador: "Administrador",
};

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
  const vacio = {
    usuario: "", nombre: "", correo: "", password: "",
    rol: "estudiante", carreras: carrera ? [carrera] : [],
  };
  const [nuevo, setNuevo] = useState(vacio);

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
    } catch (e) { fallar(e.message); }
  }

  function marcarCarrera(c) {
    const ya = nuevo.carreras.includes(c);
    setNuevo({ ...nuevo, carreras: ya ? nuevo.carreras.filter((x) => x !== c) : [...nuevo.carreras, c] });
  }

  function crear() {
    hacer(async () => {
      await api.usuarios.crear(nuevo);
      setNuevo(vacio);
    }, `Usuario "${nuevo.usuario}" creado.`);
  }

  function cambiarRol(u, rol) {
    if (u.rol === rol || !confirm(`¿Cambiar el rol de "${u.usuario}" a ${NOMBRE_ROL[rol]}?`)) return;
    hacer(() => api.usuarios.actualizar(u.usuario, { rol }), `Rol de "${u.usuario}" actualizado.`);
  }

  function resetearPassword(u) {
    const p = prompt(`Nueva contraseña para "${u.usuario}" (mínimo 6 caracteres):`);
    if (!p || !p.trim()) return;
    hacer(() => api.usuarios.actualizar(u.usuario, { nuevo_password: p }),
          `Contraseña de "${u.usuario}" cambiada. Sus sesiones activas se cerraron.`);
  }

  function borrar(u) {
    if (!confirm(`¿Borrar al usuario "${u.usuario}"? Esta acción es irreversible.`)) return;
    hacer(() => api.usuarios.borrar(u.usuario), `Usuario "${u.usuario}" borrado.`);
  }

  const necesitaCarrera = nuevo.rol !== "administrador";
  const formularioValido = nuevo.usuario.trim() && nuevo.nombre.trim() && nuevo.correo.trim()
    && nuevo.password.length >= 6 && (!necesitaCarrera || nuevo.carreras.length > 0);

  return (
    <section className="admin-seccion">
      <h3>Usuarios</h3>
      <p className="admin-nota">
        {esAdmin
          ? "Como administrador gestionas a todos los usuarios, incluidos coordinadores y administradores."
          : "Como coordinación gestionas a los estudiantes y docentes de tus carreras."}
        {" "}Cambiar la contraseña o desactivar a alguien cierra sus sesiones activas.
      </p>

      <h4>Crear nuevo usuario</h4>
      <div className="fila">
        <label>Usuario:
          <input value={nuevo.usuario} placeholder="ej: jperez"
                 onChange={(e) => setNuevo({ ...nuevo, usuario: e.target.value })} />
        </label>
        <label>Nombre completo:
          <input value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} />
        </label>
        <label>Correo:
          <input type="email" value={nuevo.correo} placeholder="jperez@utpl.edu.ec"
                 onChange={(e) => setNuevo({ ...nuevo, correo: e.target.value })} />
        </label>
        <label>Contraseña (mín. 6):
          <input type="password" value={nuevo.password}
                 onChange={(e) => setNuevo({ ...nuevo, password: e.target.value })} />
        </label>
        <label>Rol:
          <select value={nuevo.rol} onChange={(e) => setNuevo({ ...nuevo, rol: e.target.value })}>
            {rolesPermitidos.map((r) => <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
          </select>
        </label>
      </div>
      <div className="fila checks">
        <span>Carreras{necesitaCarrera ? "" : " (opcional)"}:</span>
        {carrerasPosibles.map((c) => (
          <label key={c}>
            <input type="checkbox" checked={nuevo.carreras.includes(c)} onChange={() => marcarCarrera(c)} /> {c}
          </label>
        ))}
        <button onClick={crear} disabled={!formularioValido}>Crear usuario</button>
      </div>

      <h4>Usuarios ({usuarios.length})</h4>
      <table className="tabla-usuarios">
        <thead>
          <tr>
            <th>Usuario</th><th>Correo</th><th>Rol</th><th>Carreras</th><th>Estado</th><th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {usuarios.map((u) => {
            const soyYo = u.usuario === usuario.usuario;
            return (
              <tr key={u.usuario} className={u.activo ? "" : "doc-inactivo"}>
                <td>
                  {u.usuario}{soyYo && <span className="chip-yo"> (tú)</span>}
                  <br /><small>{u.nombre}</small>
                </td>
                <td>{u.correo}</td>
                <td>
                  <select value={u.rol} disabled={soyYo} onChange={(e) => cambiarRol(u, e.target.value)}>
                    {(rolesPermitidos.includes(u.rol) ? rolesPermitidos : [u.rol]).map((r) =>
                      <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
                  </select>
                </td>
                <td>{u.carreras.join(", ") || "—"}</td>
                <td>
                  <button className="btn-secundario" disabled={soyYo} title="Clic para cambiar"
                          onClick={() => hacer(() => api.usuarios.actualizar(u.usuario, { activo: !u.activo }),
                                               `Usuario "${u.usuario}" ${u.activo ? "desactivado" : "activado"}.`)}>
                    {u.activo ? "Activo" : "Inactivo"}
                  </button>
                </td>
                <td>
                  <button className="btn-secundario" onClick={() => resetearPassword(u)}>Cambiar contraseña</button>
                  <button className="btn-peligro" disabled={soyYo} onClick={() => borrar(u)}>Borrar</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
