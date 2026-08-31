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
 * El estudiante ve solo el Chat. El docente y coordinacion ven un tab
 * mas para gestion (Admin: documentos + metricas).
 */
export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [vista, setVista] = useState("chat"); // "chat" | "admin"

  // al cargar, si hay token guardado, preguntamos "quien soy"
  useEffect(() => {
    if (!getToken()) { setCargando(false); return; }
    api.me()
      .then(setUsuario)
      .catch(() => clearToken())
      .finally(() => setCargando(false));
  }, []);

  function cerrarSesion() {
    api.logout().catch(() => {});
    clearToken();
    setUsuario(null);
  }

  if (cargando) return <div className="pantalla">Cargando...</div>;
  if (!usuario) return <Login onOk={setUsuario} />;

  const puedeAdmin = usuario.rol === "docente" || usuario.rol === "coordinacion";

  return (
    <div className="app">
      <header className="barra">
        <div className="marca">Asistente de Practicum · UTPL</div>
        <div className="tabs">
          <button
            className={vista === "chat" ? "activo" : ""}
            onClick={() => setVista("chat")}
          >Chat</button>
          {puedeAdmin && (
            <button
              className={vista === "admin" ? "activo" : ""}
              onClick={() => setVista("admin")}
            >Gestion</button>
          )}
        </div>
        <div className="sesion">
          <span>{usuario.usuario} · {usuario.rol}</span>
          <button onClick={cerrarSesion}>Salir</button>
        </div>
      </header>

      <main className="lienzo">
        {vista === "chat"
          ? <Chat carrera={usuario.carrera} />
          : <Admin usuario={usuario} />}
      </main>
    </div>
  );
}
