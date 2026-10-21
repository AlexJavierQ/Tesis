import { useEffect, useRef, useState } from "react";
import {
  Bot, Plus, Trash2, Send, FileText, Sparkles, MessageSquare, BookOpen, Layers,
  Library, TriangleAlert, CircleHelp,
} from "lucide-react";
import { api } from "../api";
import { Insignia, Segmentado } from "./ui";

// preguntas de ejemplo para la pantalla de bienvenida
const SUGERENCIAS = [
  "¿Cuántas horas de prácticas necesito en total?",
  "¿Cuál es el plazo para entregar el informe final?",
  "¿Qué formato uso para el plan de prácticas?",
  "¿Qué nota necesito para aprobar el Prácticum?",
];

// desde donde se busca la respuesta (rag.modo_efectivo en el backend)
const AYUDA_MODO = {
  general: "Se buscan solo los reglamentos generales de tu carrera.",
  curso: "Se busca solo en el material del curso elegido.",
  ambos: "Se buscan los dos y la respuesta separa lo general de lo propio del curso.",
};

/**
 * Chat con HISTORIAL persistente.
 *  - columna izquierda: "Mis conversaciones" + boton de nueva.
 *  - derecha: arriba se elige desde donde responder; en el centro los mensajes.
 * Cada pregunta se guarda en la conversacion activa (en la BD).
 */
export default function Chat({ carrera }) {
  const [cursos, setCursos] = useState([]);
  const [modo, setModo] = useState("general");      // general | curso | ambos
  const [curso, setCurso] = useState("");
  const [pregunta, setPregunta] = useState("");
  const [mensajes, setMensajes] = useState([]);     // mensajes visibles
  const [esperando, setEsperando] = useState(false);
  const [conversaciones, setConversaciones] = useState([]);
  const [convActual, setConvActual] = useState(null);  // id de la conversacion abierta
  const finHilo = useRef(null);

  useEffect(() => {
    if (carrera) api.cursos(carrera).then((cs) => {
      setCursos(cs);
      setCurso(cs[0] || "");
    }).catch(() => setCursos([]));
  }, [carrera]);

  useEffect(() => { recargarConversaciones(); }, []);

  // baja automaticamente al ultimo mensaje
  useEffect(() => { finHilo.current?.scrollIntoView({ behavior: "smooth" }); }, [mensajes, esperando]);

  async function recargarConversaciones() {
    try { setConversaciones(await api.conversaciones.listar()); }
    catch { /* sin sesion o error: lista vacia */ }
  }

  function nuevaConversacion() {
    // no se crea en la BD hasta la primera pregunta (evita conversaciones vacias)
    setConvActual(null);
    setMensajes([]);
  }

  async function abrirConversacion(id) {
    try {
      const msgs = await api.conversaciones.ver(id);
      setConvActual(id);
      setMensajes(msgs.map((m) => ({ rol: m.rol, texto: m.texto, citas: m.citas })));
    } catch (e) { alert("No se pudo abrir la conversación: " + e.message); }
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

  async function enviar(texto) {
    const q = texto.trim();
    if (!q || esperando) return;
    setPregunta("");

    // asegurar que hay una conversacion activa (crearla con la 1a pregunta)
    let convId = convActual;
    if (!convId) {
      try {
        convId = (await api.conversaciones.crear(q)).id;
        setConvActual(convId);
      } catch { /* sin sesion: se sigue sin guardar */ }
    }

    setMensajes((m) => [...m, { rol: "user", texto: q }]);
    setEsperando(true);
    try {
      const usaCurso = modo !== "general";
      const r = await api.preguntar(q, carrera, usaCurso ? curso : null, modo, convId);
      setMensajes((m) => [...m, {
        rol: "bot", texto: r.respuesta, citas: r.citas,
        conRespaldo: r.con_respaldo, degradado: r.degradado,
        // si la memoria reescribio la pregunta, se muestra como se entendio
        interpretada: r.pregunta_interpretada !== q ? r.pregunta_interpretada : null,
      }]);
      recargarConversaciones();
    } catch (err) {
      setMensajes((m) => [...m, { rol: "bot", error: true, texto: "No se pudo contactar al servidor: " + err.message }]);
    } finally {
      setEsperando(false);
    }
  }

  const opcionesModo = [
    { valor: "general", texto: "Reglamento general", icono: Library },
    { valor: "curso", texto: "Solo un curso", icono: BookOpen, deshabilitado: !cursos.length },
    { valor: "ambos", texto: "General + curso", icono: Layers, deshabilitado: !cursos.length },
  ];

  return (
    <div className="chat-layout">
      {/* ---- columna de conversaciones ---- */}
      <aside className="conversaciones">
        <button className="btn btn-primario" onClick={nuevaConversacion}>
          <Plus size={18} />Nueva conversación
        </button>
        <h3>Mis conversaciones</h3>
        {conversaciones.length === 0
          ? <p className="vacio">Aún no tienes conversaciones guardadas.</p>
          : <ul className="lista-conversaciones">
              {conversaciones.map((co) => (
                <li key={co.id} className={"conversacion" + (co.id === convActual ? " activa" : "")}
                    onClick={() => abrirConversacion(co.id)}>
                  <span className="conversacion-titulo">{co.titulo}</span>
                  <span className="conversacion-meta">{co.mensajes} mensajes · {co.iniciada_en.slice(0, 16)}</span>
                  <button className="btn btn-fantasma btn-icono" title="Borrar conversación"
                          onClick={(e) => borrarConversacion(co.id, e)}>
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>}
      </aside>

      {/* ---- chat ---- */}
      <section className="chat">
        <div className="chat-cabecera">
          <span className="etiqueta">Responder desde</span>
          <Segmentado opciones={opcionesModo} valor={modo} onChange={setModo} />
          {modo !== "general" && (
            <select value={curso} onChange={(e) => setCurso(e.target.value)} aria-label="Curso">
              {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          )}
          <span className="ayuda">{AYUDA_MODO[modo]}</span>
        </div>

        <div className="hilo">
          <div className="hilo-interior">
            {mensajes.length === 0 && (
              <div className="bienvenida">
                <div className="marca-logo"><MessageSquare size={26} /></div>
                <h2>¿En qué te ayudo con tus prácticas?</h2>
                <p>Respondo con los reglamentos y documentos oficiales, y te indico de qué
                  archivo y página sale cada dato.</p>
                <div className="sugerencias">
                  {SUGERENCIAS.map((s) => (
                    <button key={s} className="sugerencia" onClick={() => enviar(s)}>
                      <CircleHelp size={17} />{s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {mensajes.map((m, i) => m.rol === "user"
              ? (
                <div key={i} className="mensaje mensaje-usuario">
                  <div className="burbuja">{m.texto}</div>
                </div>
              ) : (
                <div key={i} className={"mensaje mensaje-bot"
                  + (m.error ? " error" : m.conRespaldo === false ? " sin-respaldo" : "")}>
                  <div className="avatar-bot"><Bot size={18} /></div>
                  <div className="burbuja">
                    {m.interpretada && (
                      <div className="interpretada">
                        <Sparkles size={14} />Entendí tu pregunta como: “{m.interpretada}”
                      </div>
                    )}
                    {m.conRespaldo === false && (
                      <div className="estado-respuesta">
                        <Insignia tipo="aviso"><TriangleAlert size={13} />Sin respaldo en los documentos</Insignia>
                      </div>
                    )}
                    {m.degradado && (
                      <div className="estado-respuesta">
                        <Insignia tipo="aviso"><TriangleAlert size={13} />
                          El modelo no respondió: se muestran los fragmentos encontrados, sin redactar
                        </Insignia>
                      </div>
                    )}
                    <div className="texto">{m.texto}</div>
                    {m.citas?.length > 0 && (
                      <div className="citas">
                        <div className="citas-titulo">Fuentes</div>
                        <div className="citas-lista">
                          {m.citas.map((c, j) => (
                            <span key={j} className="cita"><FileText size={14} />{c.fuente} · pág. {c.pagina}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

            {esperando && (
              <div className="mensaje mensaje-bot">
                <div className="avatar-bot"><Bot size={18} /></div>
                <div className="burbuja cargando"><span className="escribiendo"><i /><i /><i /></span></div>
              </div>
            )}
            <div ref={finHilo} />
          </div>
        </div>

        <div className="entrada">
          <form onSubmit={(e) => { e.preventDefault(); enviar(pregunta); }}>
            <input value={pregunta} onChange={(e) => setPregunta(e.target.value)}
                   placeholder="Escribe tu pregunta sobre las prácticas…" disabled={esperando} />
            <button type="submit" className="btn btn-primario" disabled={esperando || !pregunta.trim()}
                    aria-label="Enviar">
              <Send size={18} />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
