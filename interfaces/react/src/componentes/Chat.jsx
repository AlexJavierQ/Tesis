import { useEffect, useRef, useState } from "react";
import {
  Bot, Plus, Trash2, Send, FileText, Sparkles, MessageSquare, TriangleAlert, CircleHelp,
} from "lucide-react";
import { api } from "../api";
import { fecha } from "../formato";
import { Insignia } from "./ui";

// preguntas de ejemplo para la pantalla de bienvenida
const SUGERENCIAS = [
  "¿Cuántas horas de prácticas necesito en total?",
  "¿Cuál es el plazo para entregar el informe final?",
  "¿Qué formato uso para el plan de prácticas?",
  "¿Qué nota necesito para aprobar el Prácticum?",
];

// desde donde se busca la respuesta, de lo mas general a lo mas especifico
// (posicion del deslizador -> modo que entiende el backend: rag.modo_efectivo)
const ALCANCES = [
  { modo: "general", texto: "Reglamento general", ayuda: "Solo los reglamentos de tu carrera." },
  { modo: "ambos", texto: "General + curso", ayuda: "Ambos; la respuesta separa lo general de lo del curso." },
  { modo: "curso", texto: "Solo el curso", ayuda: "Solo el material del curso elegido." },
];

/**
 * Chat con HISTORIAL persistente.
 *  - columna izquierda: "Mis conversaciones" + boton de nueva.
 *  - derecha: arriba se elige desde donde responder; en el centro los mensajes.
 * Cada pregunta se guarda en la conversacion activa (en la BD).
 */
export default function Chat({ carrera }) {
  const [cursos, setCursos] = useState([]);
  const [nivel, setNivel] = useState(0);            // posicion del deslizador (ALCANCES)
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
      const { modo } = ALCANCES[nivel];
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

  const alcance = ALCANCES[nivel];
  const sinCursos = cursos.length === 0;

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
                <li key={co.id} className={"conversacion" + (co.id === convActual ? " activa" : "")}>
                  <button className="conversacion-abrir" onClick={() => abrirConversacion(co.id)}
                          aria-current={co.id === convActual ? "true" : undefined}>
                    <span className="conversacion-titulo">{co.titulo}</span>
                    <span className="conversacion-meta">{fecha(co.iniciada_en)}</span>
                  </button>
                  <button className="btn btn-fantasma btn-icono" title="Borrar conversación"
                          aria-label={`Borrar la conversación «${co.titulo}»`}
                          onClick={(e) => borrarConversacion(co.id, e)}>
                    <Trash2 size={15} />
                  </button>
                </li>
              ))}
            </ul>}
      </aside>

      {/* ---- chat ---- */}
      <section className="chat">
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
                            <span key={j} className="cita"><FileText size={14} />{c.fuente}, pág. {c.pagina}</span>
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
          <form className="compositor" onSubmit={(e) => { e.preventDefault(); enviar(pregunta); }}>
            <input value={pregunta} onChange={(e) => setPregunta(e.target.value)}
                   placeholder="Escribe tu pregunta sobre las prácticas…" disabled={esperando}
                   aria-label="Pregunta" />
            <div className="compositor-pie">
              <div className="alcance">
                <div className="alcance-texto">
                  <span>Buscar en</span>
                  <strong>{alcance.texto}</strong>
                </div>
                <div className="deslizador" style={{ "--pos": nivel / (ALCANCES.length - 1) }}
                     title={sinCursos ? "Tu carrera aún no tiene cursos" : alcance.ayuda}>
                  <input type="range" min={0} max={ALCANCES.length - 1} step={1}
                         value={nivel} disabled={sinCursos}
                         onChange={(e) => setNivel(Number(e.target.value))}
                         aria-label="Dónde buscar la respuesta" aria-valuetext={alcance.texto} />
                  <div className="deslizador-marcas" aria-hidden="true"><i /><i /><i /></div>
                </div>
              </div>
              {alcance.modo !== "general" && (
                <select value={curso} onChange={(e) => setCurso(e.target.value)} aria-label="Curso">
                  {cursos.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              )}
              <button type="submit" className="btn btn-primario" disabled={esperando || !pregunta.trim()}
                      aria-label="Enviar pregunta">
                <Send size={18} />
              </button>
              <span className="alcance-ayuda">
                {sinCursos ? "Tu carrera aún no tiene cursos: se buscará en los reglamentos generales." : alcance.ayuda}
              </span>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
