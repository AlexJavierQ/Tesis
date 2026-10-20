import { useEffect, useState } from "react";
import { api, getToken, clearToken } from "./api";
import Login from "./componentes/Login";
import Chat from "./componentes/Chat";
import Admin from "./componentes/Admin";
import "./estilos.css";

/**
 * Componente raiz.
 * Dos estados posibles: sin sesion -> Login. Con sesion -> app segun rol.
 *
 *   estudiante              -> solo Chat
 *   docente / coordinacion  -> Chat + Gestion
 *   administrador           -> solo Gestion (configura el sistema; no tiene
 *                              carrera, asi que no usa el chat)
 */
export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [vista, setVista] = useState("chat");   // "chat" | "admin"
  const [carrera, setCarrera] = useState(null); // carrera activa (un usuario puede tener varias)

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
    setVista(u.rol === "administrador" ? "admin" : "chat");
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

  if (cargando) return <div className="pantalla">Cargando...</div>;
  if (!usuario) return <Login onOk={entrar} />;

  const usaChat = usuario.rol !== "administrador";
  const puedeGestionar = usuario.rol !== "estudiante";

  return (
    <div className="app">
      <header className="barra">
        <div className="marca">Asistente de Practicum · UTPL</div>
        <div className="tabs">
          {usaChat && (
            <button className={vista === "chat" ? "activo" : ""}
                    onClick={() => setVista("chat")}>Chat</button>
          )}
          {puedeGestionar && (
            <button className={vista === "admin" ? "activo" : ""}
                    onClick={() => setVista("admin")}>Gestión</button>
          )}
        </div>
        <div className="sesion">
          {usuario.carreras.length > 1
            ? <select value={carrera} onChange={(e) => setCarrera(e.target.value)}>
                {usuario.carreras.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            : carrera && <span>{carrera}</span>}
          <span>{usuario.nombre} · {usuario.rol}</span>
          <button onClick={cerrarSesion}>Salir</button>
        </div>
      </header>

      <main className="lienzo">
        {vista === "chat" && usaChat
          ? <Chat key={carrera} carrera={carrera} />
          : <Admin key={carrera} usuario={usuario} carrera={carrera}
                   refrescarUsuario={refrescarUsuario} />}
      </main>
    </div>
  );
}
