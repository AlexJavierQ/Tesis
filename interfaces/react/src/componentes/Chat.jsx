import { useEffect, useState } from "react";
import { api } from "../api";

/**
 * Chat del estudiante con HISTORIAL persistente.
 *  - panel izquierdo: lista de "Mis conversaciones" + boton de nueva.
 *  - panel derecho: el chat de la conversacion activa.
 * Cada pregunta se guarda en la conversacion activa (en la BD). Al abrir una
 * conversacion pasada, se recargan sus mensajes.
 */
export default function Chat({ carrera }) {
  const [cursos, setCursos] = useState([]);
  const [modo, setModo] = useState("general");      // general | curso | ambos
  const [curso, setCurso] = useState("");
  const [pregunta, setPregunta] = useState("");
  const [historial, setHistorial] = useState([]);   // mensajes visibles
  const [esperando, setEsperando] = useState(false);

  const [conversaciones, setConversaciones] = useState([]);
  const [convActual, setConvActual] = useState(null);  // id de la conversacion abierta

  useEffect(() => {
    if (carrera) api.cursos(carrera).then(cs => {
      setCursos(cs);
      setCurso(cs[0] || "");
    }).catch(() => setCursos([]));
  }, [carrera]);

  useEffect(() => { recargarConversaciones(); }, []);

  async function recargarConversaciones() {
    try { setConversaciones(await api.conversaciones.listar()); }
    catch { /* sin sesion o error: lista vacia */ }
  }

  function nuevaConversacion() {
    // no se crea en la BD hasta la primera pregunta (evita conversaciones vacias)
    setConvActual(null);
    setHistorial([]);
  }

  async function abrirConversacion(id) {
    try {
      const msgs = await api.conversaciones.ver(id);
      setConvActual(id);
      setHistorial(msgs.map(m => ({ rol: m.rol, texto: m.texto, citas: m.citas })));
    } catch (e) { alert("No pude abrir la conversación: " + e.message); }
  }

  async function borrarConversacion(id, e) {
    e.stopPropagation();
    if (!confirm("¿Borrar esta conversación?")) return;
    try {
      await api.conversaciones.borrar(id);
      if (id === convActual) nuevaConversacion();
      recargarConversaciones();
    } catch (err) { alert(err.message); }
  }

  async function enviar(e) {
    e.preventDefault();
    const q = pregunta.trim();
    if (!q || esperando) return;
    setPregunta("");

    // asegurar que hay una conversacion activa (crearla con la 1a pregunta)
    let convId = convActual;
    if (!convId) {
      try {
        const r = await api.conversaciones.crear(q);
        convId = r.id;
        setConvActual(convId);
      } catch { /* sin sesion: se sigue sin guardar */ }
    }

    setHistorial(h => [...h, { rol: "user", texto: q }]);
    setEsperando(true);
    try {
      const usaCurso = modo !== "general";
      const r = await api.preguntar(q, carrera, usaCurso ? curso : null, modo, convId);
      setHistorial(h => [...h, {
        rol: "bot", texto: r.respuesta, citas: r.citas, conRespaldo: r.con_respaldo,
        // si la memoria reescribio la pregunta, se muestra como se entendio
        interpretada: r.pregunta_interpretada !== q ? r.pregunta_interpretada : null,
      }]);
      recargarConversaciones();
    } catch (err) {
      setHistorial(h => [...h, {
        rol: "bot", error: true,
        texto: "No pude contactar la API: " + err.message,
      }]);
    } finally {
      setEsperando(false);
    }
  }

  return (
    <div className="chat-layout">
      {/* ---- panel de conversaciones ---- */}
      <aside className="conversaciones">
        <button className="nueva-conv" onClick={nuevaConversacion}>+ Nueva conversación</button>
        <h4>Mis conversaciones</h4>
        {conversaciones.length === 0
          ? <p className="vacio-chico">Aún no tienes conversaciones.</p>
          : <ul>
              {conversaciones.map(co => (
                <li
                  key={co.id}
                  className={co.id === convActual ? "activa" : ""}
                  onClick={() => abrirConversacion(co.id)}
                >
                  <span className="conv-titulo">{co.titulo}</span>
                  <span className="conv-meta">{co.mensajes} mensajes · {co.iniciada_en}</span>
                  <button className="conv-borrar" onClick={(e) => borrarConversacion(co.id, e)}>×</button>
                </li>
              ))}
            </ul>}
      </aside>

      {/* ---- chat ---- */}
      <div className="chat">
        <div className="contexto">
          <span>Responder desde:</span>
          <label><input type="radio" checked={modo === "general"}
                        onChange={() => setModo("general")} /> Reglamento general</label>
          <label><input type="radio" checked={modo === "curso"} disabled={!cursos.length}
                        onChange={() => setModo("curso")} /> Solo un curso</label>
          <label><input type="radio" checked={modo === "ambos"} disabled={!cursos.length}
                        onChange={() => setModo("ambos")} /> General + curso</label>
          {modo !== "general" && (
            <select value={curso} onChange={(e) => setCurso(e.target.value)}>
              {cursos.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          )}
          <small className="contexto-ayuda">
            {modo === "general" && "Solo se buscan los reglamentos generales de la carrera."}
            {modo === "curso" && "Solo se busca en el material del curso elegido."}
            {modo === "ambos" && "Se buscan ambos y la respuesta distingue lo general de lo del curso."}
          </small>
        </div>

        <div className="hilo">
          {historial.length === 0 && (
            <p className="vacio">Pregúntame algo sobre el Prácticum.</p>
          )}
          {historial.map((m, i) => (
            <div key={i} className={"msg msg-" + m.rol + (m.error ? " error" : "")}>
              {m.interpretada && (
                <p className="interpretada">Entendí tu pregunta como: “{m.interpretada}”</p>
              )}
              <p>{m.texto}</p>
              {m.citas?.length > 0 && (
                <div className="citas">
                  <strong>De dónde lo saqué:</strong>
                  {m.citas.map((c, j) => (
                    <span key={j} className="cita">{c.fuente} · pág. {c.pagina}</span>
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
    </div>
  );
}
