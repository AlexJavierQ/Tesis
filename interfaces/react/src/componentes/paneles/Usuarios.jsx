import { Fragment, useEffect, useState } from "react";
import { UserPlus, Search, KeyRound, Trash2, Users, Pencil, Check, X } from "lucide-react";
import { api } from "../../api";
import { NOMBRE_ROL } from "../../navegacion";
import { nombre } from "../../formato";
import { Encabezado, Tarjeta, Insignia, Segmentado, PanelFormulario, Vacio } from "../ui";

/**
 * Gestion de usuarios.
 *  - administrador: todos los usuarios, cualquier rol y carrera (asi asigna
 *    a cada coordinador sus carreras).
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
  const [editando, setEditando] = useState(null);     // usuario cuyas carreras se editan
  const [borrador, setBorrador] = useState([]);

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

  async function guardarCarreras(u) {
    const ok = await hacer(() => api.usuarios.actualizar(u.usuario, { carreras: borrador }),
                           `Carreras de ${u.nombre} actualizadas.`);
    if (ok) setEditando(null);
  }

  const texto = busqueda.trim().toLowerCase();
  const visibles = usuarios.filter((u) =>
    (filtroRol === "todos" || u.rol === filtroRol)
    && (!texto || [u.usuario, u.nombre, u.correo].some((v) => v.toLowerCase().includes(texto))));

  const filtros = [{ valor: "todos", texto: "Todos" },
    ...rolesPermitidos.map((r) => ({ valor: r, texto: NOMBRE_ROL[r] }))];

  return (
    <>
      <Encabezado titulo="Usuarios"
                  descripcion={esAdmin
                    ? "Todas las cuentas de la plataforma. Las carreras de un coordinador son las que coordina."
                    : "Estudiantes y docentes de tus carreras."}>
        {!creando && (
          <button className="btn btn-primario" onClick={() => setCreando(true)}>
            <UserPlus size={18} />Nuevo usuario
          </button>
        )}
      </Encabezado>

      {creando && (
        <NuevoUsuario roles={rolesPermitidos} carreras={carrerasPosibles} carreraInicial={carrera}
                      onCerrar={() => setCreando(false)}
                      onCrear={async (datos) => {
                        const ok = await hacer(() => api.usuarios.crear(datos), `${datos.nombre} fue creado.`);
                        if (ok) setCreando(false);
                      }} />
      )}

      <Tarjeta>
        <div className="herramientas">
          <div className="buscador">
            <Search size={17} />
            <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)}
                   placeholder="Buscar por nombre, usuario o correo" aria-label="Buscar usuarios" />
          </div>
          <Segmentado opciones={filtros} valor={filtroRol} onChange={setFiltroRol} etiqueta="Filtrar por rol" />
        </div>

        {visibles.length === 0
          ? <Vacio icono={Users} titulo="No hay usuarios que coincidan">Prueba con otra búsqueda o filtro.</Vacio>
          : <div className="tabla-envoltura">
              <table className="tabla">
                <thead>
                  <tr><th>Persona</th><th>Rol</th><th>Carreras</th><th>Estado</th><th><span className="oculto">Acciones</span></th></tr>
                </thead>
                <tbody>
                  {visibles.map((u) => {
                    const soyYo = u.usuario === usuario.usuario;
                    const puedeCarreras = u.rol !== "administrador";
                    return (
                      <Fragment key={u.usuario}>
                      <tr>
                        <td>
                          <strong>{u.nombre}</strong>{soyYo && <> <Insignia tipo="primario">Tú</Insignia></>}
                          <div className="secundario">{u.correo}</div>
                          <div className="secundario">Usuario: {u.usuario}</div>
                        </td>
                        <td>
                          <select value={u.rol} disabled={soyYo} aria-label={`Rol de ${u.nombre}`}
                                  onChange={(e) => cambiarRol(u, e.target.value)}>
                            {(rolesPermitidos.includes(u.rol) ? rolesPermitidos : [u.rol]).map((r) =>
                              <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
                          </select>
                        </td>
                        <td>
                          <div className="fila-meta">
                            {u.carreras.length
                              ? u.carreras.map((c) => <Insignia key={c}>{nombre(c)}</Insignia>)
                              : <span className="secundario">Ninguna</span>}
                            {puedeCarreras && editando !== u.usuario && (
                              <button className="btn btn-fantasma btn-icono" title="Editar carreras"
                                      aria-label={`Editar carreras de ${u.nombre}`}
                                      onClick={() => { setEditando(u.usuario); setBorrador(u.carreras); }}>
                                <Pencil size={15} />
                              </button>
                            )}
                          </div>
                        </td>
                        <td>
                          <button className="btn btn-fantasma btn-chico" disabled={soyYo}
                                  title={u.activo ? "Desactivar: ya no podrá iniciar sesión" : "Activar"}
                                  onClick={() => hacer(() => api.usuarios.actualizar(u.usuario, { activo: !u.activo }),
                                    `${u.nombre} ${u.activo ? "desactivado: ya no puede iniciar sesión" : "activado"}.`)}>
                            {u.activo ? <Insignia tipo="exito">Activo</Insignia> : <Insignia>Inactivo</Insignia>}
                          </button>
                        </td>
                        <td>
                          <div className="fila-acciones-derecha">
                            <button className="btn btn-fantasma btn-icono" title="Cambiar contraseña"
                                    aria-label={`Cambiar contraseña de ${u.nombre}`}
                                    onClick={() => cambiarPassword(u)}><KeyRound size={16} /></button>
                            <button className="btn btn-peligro btn-icono" title="Eliminar usuario"
                                    aria-label={`Eliminar a ${u.nombre}`}
                                    disabled={soyYo} onClick={() => borrar(u)}><Trash2 size={16} /></button>
                          </div>
                        </td>
                      </tr>
                      {editando === u.usuario && (
                        <tr className="fila-edicion">
                          <td colSpan={5}>
                            <div className="campo">
                              <span>Carreras de {u.nombre}</span>
                              <div className="casillas">
                                {carrerasPosibles.map((c) => (
                                  <label key={c} className="casilla">
                                    <input type="checkbox" checked={borrador.includes(c)}
                                           onChange={() => setBorrador(borrador.includes(c)
                                             ? borrador.filter((x) => x !== c) : [...borrador, c])} />
                                    {nombre(c)}
                                  </label>
                                ))}
                              </div>
                              {u.rol === "coordinacion" && <small>Son las carreras que esta persona coordina.</small>}
                            </div>
                            <div className="fila-acciones derecha" style={{ marginTop: 14 }}>
                              <button className="btn btn-fantasma btn-chico" onClick={() => setEditando(null)}>
                                <X size={15} />Cancelar
                              </button>
                              <button className="btn btn-primario btn-chico" disabled={!borrador.length}
                                      onClick={() => guardarCarreras(u)}>
                                <Check size={15} />Guardar carreras
                              </button>
                            </div>
                          </td>
                        </tr>
                      )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>}
      </Tarjeta>
    </>
  );
}

/** Formulario de alta, desplegado en la pagina con espacio para cada campo. */
function NuevoUsuario({ roles, carreras, carreraInicial, onCerrar, onCrear }) {
  const [d, setD] = useState({
    usuario: "", nombre: "", correo: "", password: "",
    rol: "estudiante", carreras: carreraInicial ? [carreraInicial] : [],
  });
  const cambiar = (campo) => (e) => setD({ ...d, [campo]: e.target.value });
  const necesitaCarrera = d.rol !== "administrador";
  const valido = Boolean(d.usuario.trim() && d.nombre.trim() && d.correo.trim()
    && d.password.length >= 6 && (!necesitaCarrera || d.carreras.length > 0));

  function marcar(c) {
    setD({ ...d, carreras: d.carreras.includes(c) ? d.carreras.filter((x) => x !== c) : [...d.carreras, c] });
  }

  return (
    <PanelFormulario titulo="Nuevo usuario" textoEnviar="Crear usuario" valido={valido}
                     descripcion="La persona podrá entrar con su usuario o con su correo."
                     onCancelar={onCerrar} onEnviar={() => onCrear(d)}>
      <div className="rejilla-campos">
        <label className="campo"><span>Nombre completo</span>
          <input value={d.nombre} onChange={cambiar("nombre")} autoFocus autoComplete="off" /></label>
        <label className="campo"><span>Correo</span>
          <input type="email" value={d.correo} onChange={cambiar("correo")}
                 placeholder="nombre@utpl.edu.ec" autoComplete="off" spellCheck={false} /></label>
        <label className="campo"><span>Usuario</span>
          <input value={d.usuario} onChange={cambiar("usuario")} placeholder="Por ejemplo, jperez"
                 autoComplete="off" spellCheck={false} /></label>
        <label className="campo"><span>Contraseña inicial</span>
          <input type="password" value={d.password} onChange={cambiar("password")} autoComplete="new-password" />
          <small>Mínimo 6 caracteres.</small></label>
        <label className="campo"><span>Rol</span>
          <select value={d.rol} onChange={cambiar("rol")}>
            {roles.map((r) => <option key={r} value={r}>{NOMBRE_ROL[r]}</option>)}
          </select></label>
      </div>
      <div className="campo" style={{ marginTop: 22 }}>
        <span>Carreras</span>
        <div className="casillas">
          {carreras.map((c) => (
            <label key={c} className="casilla">
              <input type="checkbox" checked={d.carreras.includes(c)} onChange={() => marcar(c)} />{nombre(c)}
            </label>
          ))}
        </div>
        <small>{necesitaCarrera
          ? "Elige al menos una. Para coordinación, son las carreras que coordinará."
          : "El administrador no necesita carreras."}</small>
      </div>
    </PanelFormulario>
  );
}
