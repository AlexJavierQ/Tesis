import { useEffect, useState } from "react";
import { api } from "./api";
import Chat from "./componentes/Chat";
import PanelAdmin from "./componentes/PanelAdmin";
import VisorPdf from "./componentes/VisorPdf";
import Icono from "./componentes/Icono";
import "./estilos.css";

/**
 * La app tiene dos caras:
 *  - el CHAT del estudiante, que es lo primero y ocupa todo (uso principal);
 *  - un PANEL para docente/coordinacion, escondido detras de un acceso discreto.
 *
 * El estudiante nunca elige "rol" ni "scope": entra y pregunta. Esa es la
 * diferencia con la version anterior, que exponia la maquinaria del sistema.
 */
export default function App() {
  const [vista, setVista] = useState("chat"); // "chat" | "admin"
  const [carrera, setCarrera] = useState("");
  const [salud, setSalud] = useState(null);
  const [docAbierto, setDocAbierto] = useState(null);
  const [fallo, setFallo] = useState(null);

  useEffect(() => {
    api.salud().then(setSalud).catch(() => setSalud(null));
    api
      .carreras()
      .then((cs) => {
        setCarrera(cs[0] || "computacion");
        setFallo(null);
      })
      .catch((e) => setFallo(e.message));
  }, []);

  if (fallo) {
    return (
      <div className="pantalla-error">
        <div className="error-icono"><Icono name="sin-conexion" size={44} /></div>
        <h1>No encuentro el servicio</h1>
        <p>Parece que el asistente no está encendido en este momento.</p>
        <p className="sub">
          Si eres quien lo administra: levanta la API con{" "}
          <code>uvicorn api:app --reload</code> y recarga la página.
        </p>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="barra">
        <div className="marca" onClick={() => setVista("chat")} role="button" tabIndex={0}>
          <span className="marca-icono" aria-hidden><Icono name="chispa" size={21} /></span>
          <span className="marca-txt">
            Asistente de Prácticum
            <small>UTPL · Computación</small>
          </span>
        </div>

        {vista === "chat" ? (
          <button className="acceso" onClick={() => setVista("admin")}>
            Soy docente o coordinación
          </button>
        ) : (
          <button className="acceso" onClick={() => setVista("chat")}>
            ← Volver al chat
          </button>
        )}
      </header>

      <main className="lienzo">
        {vista === "chat" ? (
          <Chat carrera={carrera} alVerCita={setDocAbierto} salud={salud} />
        ) : (
          <PanelAdmin carrera={carrera} alVerDoc={setDocAbierto} />
        )}
      </main>

      {docAbierto && <VisorPdf doc={docAbierto} alCerrar={() => setDocAbierto(null)} />}
    </div>
  );
}
