import { useEffect, useRef, useState } from "react";
import { GraduationCap, LogOut } from "lucide-react";
import { api, getToken, clearToken } from "./api";
import { MENU, NOMBRE_ROL } from "./navegacion";
import { Notificaciones } from "./componentes/ui";
import Login from "./componentes/Login";
import Chat from "./componentes/Chat";
import Documentos from "./componentes/paneles/Documentos";
import Estructura from "./componentes/paneles/Estructura";
import Metricas from "./componentes/paneles/Metricas";
import Usuarios from "./componentes/paneles/Usuarios";
import Configuracion from "./componentes/paneles/Configuracion";
import Registro from "./componentes/paneles/Registro";
import "./estilos.css";

// que componente muestra cada seccion del menu
const PANTALLAS = {
  documentos: Documentos,
  estructura: Estructura,
  metricas: Metricas,
  usuarios: Usuarios,
  configuracion: Configuracion,
  registro: Registro,
};

/**
 * Componente raiz.
 * Sin sesion -> Login. Con sesion -> barra lateral (menu segun el rol,
 * en navegacion.js) + la pantalla elegida.
 */
export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [seccion, setSeccion] = useState(null);
  const [carrera, setCarrera] = useState(null);  // carrera activa (un usuario puede tener varias)
  const [avisos, setAvisos] = useState([]);
  const contador = useRef(0);

  // al cargar, si hay token guardado, preguntamos "quien soy"
  useEffect(() => {
    if (!getToken()) { setCargando(false); return; }
    api.me()
      .then(entrar)
      .catch(() => clearToken())
      .finally(() => setCargando(false));
  }, []);

  function entrar(u) {
    setUsuario(u);
    setCarrera(u.carreras[0] || null);
    setSeccion(MENU[u.rol][0].secciones[0].clave);   // primera seccion de su menu
  }

  // vuelve a pedir /me (p. ej. la coordinacion creo una carrera y ahora la tiene)
  function refrescarUsuario() {
    api.me().then(setUsuario).catch(() => {});
  }

  function cerrarSesion() {
    api.logout().catch(() => {});
    clearToken();
    setUsuario(null);
  }

  // avisos flotantes: desaparecen solos a los 5 segundos
  function notificar(tipo, texto) {
    const id = ++contador.current;
    setAvisos((a) => [...a, { id, tipo, texto }]);
    setTimeout(() => quitarAviso(id), 5000);
  }
  function quitarAviso(id) {
    setAvisos((a) => a.filter((n) => n.id !== id));
  }

  if (cargando) return <div className="pantalla">Cargando…</div>;
  if (!usuario) return <Login onOk={entrar} />;

  const Pantalla = PANTALLAS[seccion];
  const iniciales = usuario.nombre.split(" ").slice(0, 2).map((p) => p[0]).join("").toUpperCase();

  return (
    <div className="app">
      <aside className="lateral">
        <div className="marca">
          <div className="marca-logo"><GraduationCap size={22} /></div>
          <div>
            <strong>Asistente de Prácticum</strong>
            <span>UTPL</span>
          </div>
        </div>

        <nav>
          {MENU[usuario.rol].map((grupo) => (
            <div key={grupo.titulo} className="nav-grupo">
              <div className="nav-grupo-titulo">{grupo.titulo}</div>
              {grupo.secciones.map(({ clave, texto, icono: Icono }) => (
                <button key={clave} className={"nav-item" + (seccion === clave ? " activo" : "")}
                        onClick={() => setSeccion(clave)}>
                  <Icono size={18} />{texto}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="lateral-pie">
          {usuario.carreras.length > 1 && (
            <label className="campo">
              <span>Carrera activa</span>
              <select value={carrera} onChange={(e) => setCarrera(e.target.value)}>
                {usuario.carreras.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          )}
          <div className="usuario-actual">
            <div className="avatar">{iniciales}</div>
            <div>
              <strong>{usuario.nombre}</strong>
              <span>{NOMBRE_ROL[usuario.rol]}{carrera && usuario.carreras.length === 1 ? ` · ${carrera}` : ""}</span>
            </div>
          </div>
          <button className="btn-salir" onClick={cerrarSesion}>
            <LogOut size={17} />Cerrar sesión
          </button>
        </div>
      </aside>

      <main className="principal">
        {seccion === "chat"
          ? <Chat key={carrera} carrera={carrera} />
          : Pantalla && (
              <div className="contenedor">
                <Pantalla key={seccion + carrera} usuario={usuario} carrera={carrera}
                          refrescarUsuario={refrescarUsuario}
                          avisar={(t) => notificar("exito", t)}
                          fallar={(t) => notificar("error", t)} />
              </div>
            )}
      </main>

      <Notificaciones lista={avisos} onCerrar={quitarAviso} />
    </div>
  );
}
