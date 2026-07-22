import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import Icono from "./Icono";

const SUGERIDAS = [
  "¿Cuántas horas de prácticas necesito?",
  "¿Cuál es el plazo para entregar el informe?",
  "¿Qué formato uso para el informe final?",
  "¿Cuál es la nota mínima para aprobar?",
];

export default function Chat({ carrera, alVerCita, salud }) {
  const [cursos, setCursos] = useState([]);
  const [curso, setCurso] = useState(""); // "" = reglamentos generales
  const [menuCurso, setMenuCurso] = useState(false);
  const [historial, setHistorial] = useState([]);
  const [texto, setTexto] = useState("");
  const [esperando, setEsperando] = useState(false);
  const finRef = useRef(null);

  useEffect(() => {
    if (carrera) api.cursos(carrera).then(setCursos).catch(() => setCursos([]));
  }, [carrera]);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [historial, esperando]);

  async function enviar(pregunta) {
    const q = (pregunta ?? texto).trim();
    if (!q || esperando) return;
    setTexto("");
    // ultimos turnos para que el asistente entienda seguimientos ("y cuantas
    // horas", "explicamelo de otra forma"). Solo texto, sin las citas.
    const previos = historial.slice(-6).map((m) => ({
      rol: m.rol === "user" ? "user" : "bot",
      texto: m.texto,
    }));
    setHistorial((h) => [...h, { rol: "user", texto: q }]);
    setEsperando(true);
    try {
      const r = await api.preguntar(q, carrera, curso || null, previos);
      setHistorial((h) => [
        ...h,
        { rol: "bot", texto: r.respuesta, citas: r.citas, conRespaldo: r.con_respaldo },
      ]);
    } catch (e) {
      setHistorial((h) => [
        ...h,
        { rol: "bot", error: true, texto: "Ups, no pude conectar. ¿Lo intentamos de nuevo?" + (e.message ? ` (${e.message})` : "") },
      ]);
    } finally {
      setEsperando(false);
    }
  }

  const contexto = curso || "General";
  const vacio = historial.length === 0;

  return (
    <div className="chat">
      {/* barra de contexto: sobre qué está preguntando, en lenguaje natural */}
      <div className="contexto">
        <span className="contexto-lbl">Preguntas sobre</span>
        <div className="selector">
          <button className="selector-btn" onClick={() => setMenuCurso((v) => !v)}>
            <Icono name={curso ? "libro" : "biblioteca"} size={15} />
            {curso || "Reglamentos generales"}
            <Icono name="abajo" size={13} className="chevron" />
          </button>
          {menuCurso && (
            <div className="selector-menu" onMouseLeave={() => setMenuCurso(false)}>
              <button
                className={!curso ? "activa" : ""}
                onClick={() => { setCurso(""); setMenuCurso(false); }}
              >
                <Icono name="biblioteca" size={15} /> Reglamentos generales
              </button>
              {cursos.map((c) => (
                <button
                  key={c}
                  className={curso === c ? "activa" : ""}
                  onClick={() => { setCurso(c); setMenuCurso(false); }}
                >
                  <Icono name="libro" size={15} /> {c}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="hilo">
        {vacio && (
          <div className="saludo">
            <div className="saludo-avatar"><Icono name="chispa" size={30} /></div>
            <h1>Hola, ¿en qué te ayudo?</h1>
            <p>
              Respondo tus dudas sobre el Prácticum (horas, plazos, formatos, notas)
              con los documentos oficiales. Cada respuesta te muestra de dónde sale.
            </p>
            <div className="chips">
              {SUGERIDAS.map((s) => (
                <button key={s} className="chip" onClick={() => enviar(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {historial.map((m, i) => (
          <Mensaje key={i} m={m} alVerCita={alVerCita} />
        ))}

        {esperando && (
          <div className="msg msg-bot">
            <div className="avatar"><Icono name="chispa" size={18} /></div>
            <div className="burbuja escribiendo">
              <span className="puntos"><i /><i /><i /></span>
            </div>
          </div>
        )}
        <div ref={finRef} />
      </div>

      <form className="barra-entrada" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Escribe tu pregunta…"
          disabled={esperando}
          autoFocus
        />
        <button type="submit" className="enviar" disabled={esperando || !texto.trim()} aria-label="Enviar">
          <Icono name="enviar" size={19} />
        </button>
      </form>
      {salud && !salud.llm_disponible && (
        <p className="nota-degradado">
          Modo sin conexión al modelo: te muestro los fragmentos oficiales tal cual.
        </p>
      )}
    </div>
  );
}

function Mensaje({ m, alVerCita }) {
  if (m.rol === "user") {
    return (
      <div className="msg msg-user">
        <div className="burbuja">{m.texto}</div>
      </div>
    );
  }
  return (
    <div className="msg msg-bot">
      <div className="avatar"><Icono name="chispa" size={18} /></div>
      <div className={`burbuja${m.error ? " burbuja-error" : ""}`}>
        <p>{m.texto}</p>

        {!m.error && !m.conRespaldo && (
          <div className="derivacion">
            No encontré esto en los documentos oficiales. Mejor consúltalo con la coordinación.
          </div>
        )}

        {m.citas?.length > 0 && (
          <div className="fuentes">
            <span className="fuentes-lbl">De dónde lo saqué</span>
            <div className="fuentes-lista">
              {m.citas.map((c, j) => (
                <button
                  key={j}
                  className="fuente"
                  onClick={() => alVerCita({ ...c, pagina: Number(c.pagina) || 1 })}
                  title="Ver la página exacta"
                >
                  <span className="fuente-doc">{c.fuente.replace(/\.pdf$/i, "")}</span>
                  <span className="fuente-pag">pág. {c.pagina}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
