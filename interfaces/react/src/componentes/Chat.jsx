import { useEffect, useState } from "react";
import { api } from "../api";

/**
 * Chat del estudiante.
 * - selecciona curso o "general" (reglamentos de la carrera)
 * - escribe pregunta -> muestra la respuesta con sus citas
 */
export default function Chat({ carrera }) {
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState("");         // "" = reglamentos generales
  const [pregunta, setPregunta] = useState("");
  const [historial, setHistorial] = useState([]); // {rol, texto, citas?}
  const [esperando, setEsperando] = useState(false);

  useEffect(() => {
    if (carrera) api.cursos(carrera).then(setCursos).catch(() => setCursos([]));
  }, [carrera]);

  async function enviar(e) {
    e.preventDefault();
    const q = pregunta.trim();
    if (!q || esperando) return;
    setPregunta("");
    setHistorial(h => [...h, { rol: "user", texto: q }]);
    setEsperando(true);
    try {
      const r = await api.preguntar(q, carrera, curso || null);
      setHistorial(h => [...h, {
        rol: "bot",
        texto: r.respuesta,
        citas: r.citas,
        conRespaldo: r.con_respaldo,
      }]);
    } catch (err) {
      setHistorial(h => [...h, {
        rol: "bot",
        error: true,
        texto: "No pude contactar la API: " + err.message,
      }]);
    } finally {
      setEsperando(false);
    }
  }

  return (
    <div className="chat">
      <div className="contexto">
        <label>Tu curso (opcional):
          <select value={curso} onChange={(e) => setCurso(e.target.value)}>
            <option value="">— ninguno —</option>
            {cursos.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <small className="contexto-ayuda">
          Siempre se buscan los reglamentos generales de la carrera.
          Si eliges un curso, tambien se buscan sus documentos.
        </small>
      </div>

      <div className="hilo">
        {historial.length === 0 && (
          <p className="vacio">Preguntame algo sobre el Practicum.</p>
        )}
        {historial.map((m, i) => (
          <div key={i} className={"msg msg-" + m.rol + (m.error ? " error" : "")}>
            <p>{m.texto}</p>
            {m.citas?.length > 0 && (
              <div className="citas">
                <strong>De donde lo saque:</strong>
                {m.citas.map((c, j) => (
                  <span key={j} className="cita">
                    {c.fuente} · pag. {c.pagina}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {esperando && <div className="msg msg-bot">Buscando...</div>}
      </div>

      <form className="barra-entrada" onSubmit={enviar}>
        <input
          value={pregunta}
          onChange={(e) => setPregunta(e.target.value)}
          placeholder="Escribe tu pregunta..."
          disabled={esperando}
        />
        <button type="submit" disabled={esperando || !pregunta.trim()}>Enviar</button>
      </form>
    </div>
  );
}
