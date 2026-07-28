import { useEffect, useState } from "react";
import { api } from "../api";
import Documentos from "./Documentos";
import Metricas from "./Metricas";
import Icono from "./Icono";

/**
 * Area de gestion para docente y coordinacion. Se llega por el acceso discreto
 * de la barra superior; el estudiante no la ve.
 *
 * Ambito:
 *  - "General" -> reglamentos de la carrera (coordinacion)
 *  - un curso  -> documentos de ese curso (docente)
 * Es el mismo eje que ya entiende la API; aqui se presenta como un simple
 * "¿sobre qué trabajas?" en vez de como una eleccion de rol.
 */
export default function PanelAdmin({ carrera, alVerDoc }) {
  const [cursos, setCursos] = useState([]);
  const [ambito, setAmbito] = useState("General"); // "General" | nombre de curso
  const [pestana, setPestana] = useState("documentos");
  const [nuevoCurso, setNuevoCurso] = useState("");

  function recargarCursos() {
    if (carrera) api.cursos(carrera).then(setCursos).catch(() => setCursos([]));
  }
  useEffect(recargarCursos, [carrera]);

  const curso = ambito === "General" ? null : ambito;

  async function crearCurso() {
    const nombre = nuevoCurso.trim();
    if (!nombre) return;
    try {
      await api.crearCurso(carrera, nombre);
      setNuevoCurso("");
      recargarCursos();
      setAmbito(nombre);
    } catch (e) {
      alert("No se pudo crear el curso: " + e.message);
    }
  }

  return (
    <div className="admin">
      <aside className="admin-lat">
        <h2>Gestión</h2>
        <p className="admin-lbl">¿Sobre qué trabajas?</p>
        <div className="ambitos">
          <button
            className={ambito === "General" ? "ambito activa" : "ambito"}
            onClick={() => setAmbito("General")}
          >
            <Icono name="biblioteca" size={16} /> Reglamentos de la carrera
          </button>
          {cursos.map((c) => (
            <button
              key={c}
              className={ambito === c ? "ambito activa" : "ambito"}
              onClick={() => setAmbito(c)}
            >
              <Icono name="libro" size={16} /> {c}
            </button>
          ))}
        </div>

        <div className="crear-curso">
          <input
            value={nuevoCurso}
            onChange={(e) => setNuevoCurso(e.target.value)}
            placeholder="Nuevo curso…"
            onKeyDown={(e) => e.key === "Enter" && crearCurso()}
          />
          <button onClick={crearCurso} disabled={!nuevoCurso.trim()}>Crear</button>
        </div>
      </aside>

      <section className="admin-main">
        <div className="admin-cab">
          <h3>{ambito === "General" ? "Reglamentos de la carrera" : `Curso: ${ambito}`}</h3>
          <p className="admin-nota">
            {ambito === "General"
              ? "Estos documentos alimentan el chat de toda la carrera."
              : "Estos documentos solo afectan al chat de este curso."}
          </p>
        </div>

        <nav className="segmentos">
          <button
            className={pestana === "documentos" ? "activa" : ""}
            onClick={() => setPestana("documentos")}
          >
            Documentos
          </button>
          <button
            className={pestana === "metricas" ? "activa" : ""}
            onClick={() => setPestana("metricas")}
          >
            Qué preguntan
          </button>
        </nav>

        {pestana === "documentos" ? (
          <Documentos carrera={carrera} curso={curso} alVerDoc={alVerDoc} />
        ) : (
          <Metricas carrera={carrera} curso={curso} />
        )}
      </section>
    </div>
  );
}
