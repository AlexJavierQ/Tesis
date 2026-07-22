/* =============================================================================
 * Asistente de Practicum - Widget embebible (HTML + CSS + JS puro)
 *
 * Tercera propuesta de frontend del MVP. Las otras dos (Streamlit y React)
 * son APLICACIONES: el usuario va a ellas. Esta es lo contrario: se INCRUSTA
 * en el portal que el estudiante ya usa, con una sola etiqueta <script>.
 *
 * Restriccion autoimpuesta: cero dependencias, cero build, cero CDN. El
 * archivo se copia a un servidor estatico y funciona. Esto demuestra que la
 * API REST es el verdadero limite del sistema: el nucleo (RAG + FastAPI) no
 * se toca ni se entera de quien lo consume.
 *
 * Se ejecuta dentro de una IIFE para no publicar ni una sola variable en el
 * ambito global del portal anfitrion.
 * ========================================================================== */
(function () {
  "use strict";

  /* ---------------------------------------------------------------------------
   * 1. Configuracion declarativa
   *
   * La config viaja en los atributos data-* de la propia etiqueta <script>.
   * Asi el integrador del portal no escribe JavaScript: solo HTML. Es el mismo
   * patron que usan los widgets de analitica o de chat comercial.
   *
   * document.currentScript hay que leerlo AHORA, en la fase sincrona: cuando
   * mas tarde se disparen los callbacks ya valdra null.
   * ------------------------------------------------------------------------ */
  var script = document.currentScript;

  var CONFIG = {
    api: (script && script.dataset.api) || "http://localhost:8000",
    carrera: (script && script.dataset.carrera) || "computacion",
    curso: (script && script.dataset.curso) || null,
  };

  // Sin barra final: todas las rutas se concatenan como "/algo".
  CONFIG.api = CONFIG.api.replace(/\/+$/, "");

  // Guarda contra una doble insercion del <script> en el portal.
  if (window.__asistentePracticumCargado) return;
  window.__asistentePracticumCargado = true;

  /* ---------------------------------------------------------------------------
   * 2. Cliente HTTP
   *
   * Unico punto del widget que sabe de HTTP. Igual que en el frontend React:
   * si el backend cambia de forma, solo se toca esta seccion.
   * ------------------------------------------------------------------------ */
  var api = {
    preguntar: function (pregunta, historial) {
      return pedirJson(CONFIG.api + "/preguntar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pregunta: pregunta,
          carrera: CONFIG.carrera,
          curso: CONFIG.curso,
          historial: historial || null,
        }),
      });
    },

    infoDocumento: function (ref) {
      return pedirJson(
        CONFIG.api + "/documentos/info?" + new URLSearchParams({ ref: ref })
      );
    },

    // URL directa de la imagen: la consume un <img>, no fetch. El navegador
    // se encarga de la descarga y de la cache (la API manda Cache-Control).
    urlPagina: function (ref, pagina) {
      return (
        CONFIG.api +
        "/documentos/pagina?" +
        new URLSearchParams({ ref: ref, pagina: pagina })
      );
    },
  };

  /**
   * Envuelve fetch para que TODO fallo llegue como Error con mensaje legible.
   * El widget vive en la pagina de otro: un error suelto en consola no basta,
   * el estudiante tiene que ver que paso.
   */
  function pedirJson(url, opciones) {
    return fetch(url, opciones).then(function (r) {
      if (!r.ok) {
        // El detalle de FastAPI es mas util que el codigo, si viene.
        return r
          .json()
          .catch(function () {
            return null;
          })
          .then(function (cuerpo) {
            throw new Error(
              (cuerpo && cuerpo.detail) || "El servicio respondio " + r.status + "."
            );
          });
      }
      return r.json();
    });
  }

  /* ---------------------------------------------------------------------------
   * 3. Estilos
   *
   * Van como texto porque el widget no puede depender de un .css externo:
   * un solo <script> tiene que bastar.
   *
   * Todo se aplica DENTRO del Shadow DOM (ver seccion 5), por eso los
   * selectores pueden ser cortos y genericos (.panel, .msg) sin miedo a
   * chocar con las clases del portal.
   * ------------------------------------------------------------------------ */
  var CSS = `
  /* 'all: initial' corta la herencia del portal anfitrion. El Shadow DOM
     bloquea los SELECTORES de fuera, pero las propiedades heredables
     (font, color, line-height) siguen entrando por el arbol: esto las para. */
  :host {
    all: initial;
    display: block;
    font-family: "Inter", "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif;
    font-size: 15px;
    line-height: 1.5;
    color: var(--tinta);

    /* Misma paleta oscura que la app React (estilos.css). */
    --bg: #0e1421;
    --surface: #151c2b;
    --surface-2: #1b2334;
    --surface-3: #232d42;
    --line: #2a3550;
    --tinta: #e7ecf6;
    --tinta-2: #b3bfd2;
    --gris: #8593ab;
    --azul: #6ea3fb;
    --azul-2: #4d80e6;
    --azul-suave: rgba(110, 163, 251, .14);
    --oro: #e0b968;
    --verde: #55c98c;
    --rojo: #f0776b;
    --grad: linear-gradient(135deg, #5b93f0, #3f68cf);
  }

  *, *::before, *::after { box-sizing: border-box; }
  svg { flex-shrink: 0; }

  /* Un unico foco visible para todo el widget: requisito de accesibilidad
     y lo primero que se pierde al estilar botones a mano. */
  :where(button, input, textarea, a):focus-visible {
    outline: 3px solid var(--azul);
    outline-offset: 2px;
  }

  /* ---------- boton flotante ---------- */
  .lanzador {
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 2147483000;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 12px 18px;
    border: 0;
    border-radius: 28px;
    background: var(--grad);
    color: #fff;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 6px 20px rgba(0,0,0,.45);
    transition: transform .12s, filter .15s;
  }
  .lanzador:hover { transform: translateY(-1px); filter: brightness(1.08); }
  .lanzador .icono { display: grid; place-items: center; }

  /* ---------- panel ---------- */
  .panel {
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 2147483001;
    display: flex;
    flex-direction: column;
    width: 380px;
    max-width: calc(100vw - 40px);
    height: 560px;
    max-height: calc(100vh - 40px);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 18px 50px rgba(0,0,0,.55);
  }
  [hidden] { display: none !important; }

  .cabecera {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    background: var(--surface-2);
    color: var(--tinta);
    border-bottom: 1px solid var(--line);
  }
  .cabecera-info { display: flex; align-items: center; gap: 11px; min-width: 0; }
  .marca-icono {
    flex: none;
    width: 36px; height: 36px;
    display: grid; place-items: center;
    background: var(--grad); color: #fff;
    border-radius: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,.35);
  }
  .cabecera h2 { margin: 0; font-size: 15px; font-weight: 700; color: var(--tinta); }
  .cabecera p  { margin: 2px 0 0; font-size: 12px; color: var(--gris); }

  .btn-icono {
    flex: none;
    width: 32px; height: 32px;
    border: 0; border-radius: 8px;
    background: transparent;
    color: var(--gris);
    display: grid; place-items: center;
    cursor: pointer;
    transition: background .15s, color .15s;
  }
  .btn-icono:hover { background: var(--surface-3); color: var(--tinta); }

  /* ---------- conversacion ---------- */
  .conversacion {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .msg { max-width: 88%; padding: 11px 14px; border-radius: 14px; box-shadow: 0 1px 2px rgba(0,0,0,.35); }
  .msg p { margin: 0 0 8px; }
  .msg p:last-child { margin-bottom: 0; }

  .msg.usuario {
    align-self: flex-end;
    background: var(--grad);
    color: #fff;
    border-bottom-right-radius: 4px;
  }
  .msg.asistente {
    align-self: flex-start;
    background: var(--surface-2);
    border: 1px solid var(--line);
    color: var(--tinta);
    border-bottom-left-radius: 4px;
  }
  .msg.error {
    align-self: stretch;
    max-width: 100%;
    background: rgba(240, 119, 107, .12);
    border: 1px solid rgba(240, 119, 107, .35);
    color: #f3a79d;
    font-size: 14px;
  }

  /* Aviso de derivacion: cuando la respuesta NO tiene respaldo documental.
     Se destaca a proposito, es la salvaguarda academica del sistema. */
  .aviso {
    margin-top: 10px;
    padding: 9px 11px;
    border-left: 3px solid var(--oro);
    background: rgba(224, 185, 104, .12);
    font-size: 13px;
    color: #e6c684;
    border-radius: 0 8px 8px 0;
  }

  /* ---------- citas ---------- */
  .citas { margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--line); }
  .citas-titulo {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: var(--gris);
    margin-bottom: 8px;
  }
  .citas-lista { display: flex; flex-wrap: wrap; gap: 6px; }
  .cita {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 11px;
    border: 1px solid transparent;
    border-radius: 10px;
    background: var(--azul-suave);
    color: var(--azul);
    font: inherit;
    font-size: 12.5px;
    font-weight: 600;
    cursor: pointer;
    text-align: left;
    transition: border-color .15s, transform .1s;
  }
  .cita:hover { border-color: var(--azul); transform: translateY(-1px); }

  /* ---------- escribiendo ---------- */
  .puntos { display: inline-flex; gap: 4px; align-items: center; }
  .puntos i {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--azul);
    opacity: .35;
    animation: latir 1.2s infinite ease-in-out;
  }
  .puntos i:nth-child(2) { animation-delay: .18s; }
  .puntos i:nth-child(3) { animation-delay: .36s; }
  @keyframes latir { 0%,80%,100% { opacity: .3 } 40% { opacity: 1 } }

  /* Respeta a quien pidio menos movimiento en su sistema operativo. */
  @media (prefers-reduced-motion: reduce) {
    .puntos i { animation: none; opacity: .6; }
  }

  /* ---------- formulario ---------- */
  .barra {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 12px;
    border-top: 1px solid var(--line);
    background: var(--surface);
  }
  .barra textarea {
    flex: 1;
    resize: none;
    min-height: 44px;
    max-height: 110px;
    padding: 11px 14px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--surface-2);
    font: inherit;
    /* 16px reales en movil: por debajo, iOS hace zoom al enfocar. */
    font-size: 16px;
    color: var(--tinta);
  }
  .barra textarea::placeholder { color: var(--gris); }
  .barra textarea:focus { border-color: var(--azul); box-shadow: 0 0 0 3px rgba(110, 163, 251, .16); }
  .enviar {
    flex: none;
    width: 44px; height: 44px;
    border: 0;
    border-radius: 50%;
    background: var(--grad);
    color: #fff;
    display: grid; place-items: center;
    cursor: pointer;
    transition: transform .12s, filter .15s;
  }
  .enviar:hover:not(:disabled) { transform: scale(1.06); filter: brightness(1.1); }
  .enviar:disabled { cursor: not-allowed; opacity: .45; }

  .pie {
    padding: 0 12px 10px;
    background: var(--surface);
    font-size: 11px;
    color: var(--gris);
    text-align: center;
  }

  /* ---------- visor de documento ---------- */
  .visor-fondo {
    position: fixed;
    inset: 0;
    z-index: 2147483002;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: rgba(4, 8, 16, .72);
    backdrop-filter: blur(3px);
  }
  .visor {
    display: flex;
    flex-direction: column;
    width: min(860px, 100%);
    height: min(92vh, 100%);
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 18px 50px rgba(0,0,0,.55);
  }
  .visor-cuerpo {
    flex: 1;
    overflow: auto;
    padding: 14px;
    background: var(--bg);
    display: flex;
    align-items: flex-start;
    justify-content: center;
  }
  .visor-cuerpo img {
    max-width: 100%;
    background: #fff;
    border-radius: 6px;
    box-shadow: 0 3px 14px rgba(0,0,0,.4);
  }
  .visor-estado { color: var(--gris); font-size: 14px; padding: 24px; text-align: center; }
  .visor-pie {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 14px;
    border-top: 1px solid var(--line);
    background: var(--surface);
  }
  .visor-pie button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 15px;
    border: 0;
    border-radius: 10px;
    background: var(--azul-suave);
    color: var(--azul);
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: background .15s;
  }
  .visor-pie button:hover:not(:disabled) { background: rgba(110, 163, 251, .24); }
  .visor-pie button:disabled { opacity: .45; cursor: not-allowed; }
  .visor-ayuda { font-size: 11.5px; color: var(--gris); }

  /* ---------- movil ---------- */
  /* Por debajo de 560px el panel ocupa la pantalla completa: en un telefono
     una ventanita flotante deja el teclado virtual encima del texto. */
  @media (max-width: 560px) {
    .panel {
      right: 0; bottom: 0; left: 0; top: 0;
      width: 100%; max-width: 100%;
      height: 100%; max-height: 100%;
      border: 0; border-radius: 0;
    }
    .lanzador { right: 14px; bottom: 14px; padding: 12px 16px; }
    .visor-fondo { padding: 0; }
    .visor { height: 100%; border-radius: 0; }
    .visor-ayuda { display: none; }
  }
  `;

  /* ---------------------------------------------------------------------------
   * 4. Utilidades de DOM
   *
   * Reemplazan a innerHTML en todo lo que venga de la API. El texto del LLM y
   * los nombres de documento son datos externos: insertarlos como HTML seria
   * una via de inyeccion. Se construyen nodos y se asigna textContent.
   * ------------------------------------------------------------------------ */
  function el(tag, clase, texto) {
    var n = document.createElement(tag);
    if (clase) n.className = clase;
    if (texto != null) n.textContent = texto;
    return n;
  }

  /** Parte el texto en parrafos respetando los saltos de linea del modelo. */
  function parrafos(contenedor, texto) {
    String(texto)
      .split(/\n{2,}|\n/)
      .filter(function (t) {
        return t.trim() !== "";
      })
      .forEach(function (t) {
        contenedor.appendChild(el("p", null, t.trim()));
      });
  }

  /* ---------------------------------------------------------------------------
   * Iconos SVG (trazo, estilo lucide). Mismos paths que el componente Icono.jsx
   * de la app React, para que las dos propuestas se sientan un solo producto.
   * Se guardan como markup y se inyectan con un <svg> construido a mano: heredan
   * el color del contexto via currentColor y no dependen de la fuente de emojis
   * del sistema operativo. La 'chispa' es el icono emblematico de la marca.
   * ------------------------------------------------------------------------ */
  var TRAZOS = {
    chispa:
      '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .962 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.962 0z" />',
    enviar:
      '<path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z" /><path d="m21.854 2.147-10.94 10.939" />',
    cerrar: '<path d="M18 6 6 18" /><path d="m6 6 12 12" />',
    izquierda: '<path d="m15 18-6-6 6-6" />',
    derecha: '<path d="m9 18 6-6-6-6" />',
    archivo:
      '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z" /><path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M16 13H8" /><path d="M16 17H8" /><path d="M10 9H8" />',
  };

  /**
   * Construye un <svg> de trazo con el mismo estandar que Icono.jsx (viewBox
   * 0 0 24 24, sin relleno, trazo currentColor de grosor 2, extremos redondos).
   * El markup interno es constante y propio del widget: no viene de la API, asi
   * que asignarlo con innerHTML aqui no abre ninguna via de inyeccion.
   */
  function icono(nombre, tam) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("width", tam || 20);
    svg.setAttribute("height", tam || 20);
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.innerHTML = TRAZOS[nombre] || "";
    return svg;
  }

  /* ---------------------------------------------------------------------------
   * 5. Shadow DOM
   *
   * ESTA es la decision central del widget. El codigo se va a inyectar en un
   * portal ajeno y desconocido, con su propio CSS (posiblemente Bootstrap,
   * reglas con !important, selectores tipo "div button { ... }").
   *
   * El shadow root crea una frontera de estilos en los dos sentidos:
   *   - hacia dentro: el CSS del portal no alcanza a los nodos del widget,
   *     asi que el asistente se ve igual en cualquier sitio;
   *   - hacia fuera: las reglas del widget no se filtran al portal, asi que
   *     integrarlo no puede romper la maquetacion existente.
   *
   * Es la alternativa honesta al <iframe>: mismo aislamiento visual, pero sin
   * segundo documento, sin problemas de altura y con acceso directo al DOM.
   * ------------------------------------------------------------------------ */
  var anfitrion = document.createElement("div");
  anfitrion.setAttribute("data-asistente-practicum", "");
  var raiz = anfitrion.attachShadow({ mode: "open" });

  var hoja = document.createElement("style");
  hoja.textContent = CSS;
  raiz.appendChild(hoja);

  /* ---------------------------------------------------------------------------
   * 6. Construccion de la interfaz
   * ------------------------------------------------------------------------ */

  // --- boton flotante ---
  var lanzador = el("button", "lanzador");
  lanzador.type = "button";
  lanzador.id = "lanzador";
  lanzador.setAttribute("aria-expanded", "false");
  lanzador.setAttribute("aria-controls", "panel");
  var lanzadorIcono = el("span", "icono");
  lanzadorIcono.appendChild(icono("chispa", 20));
  lanzador.appendChild(lanzadorIcono);
  lanzador.appendChild(el("span", null, "Asistente de Prácticum"));
  raiz.appendChild(lanzador);

  // --- panel ---
  var panel = el("div", "panel");
  panel.id = "panel";
  panel.hidden = true;
  // role=dialog + aria-label: el lector de pantalla anuncia que se abrio una
  // region nueva. No se usa aria-modal porque el portal sigue siendo usable.
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Asistente de Prácticum");

  var cabecera = el("header", "cabecera");
  var cabInfo = el("div", "cabecera-info");
  // La chispa es el icono emblematico de la marca: el mismo del lanzador,
  // aqui hace de avatar del asistente en la cabecera del panel.
  var marcaIcono = el("div", "marca-icono");
  marcaIcono.appendChild(icono("chispa", 20));
  cabInfo.appendChild(marcaIcono);
  var titulos = el("div");
  titulos.appendChild(el("h2", null, "Asistente de Prácticum"));
  titulos.appendChild(
    el(
      "p",
      null,
      CONFIG.curso
        ? CONFIG.carrera + " · " + CONFIG.curso
        : CONFIG.carrera + " · normativa general"
    )
  );
  cabInfo.appendChild(titulos);
  var btnCerrar = el("button", "btn-icono");
  btnCerrar.type = "button";
  btnCerrar.setAttribute("aria-label", "Cerrar el asistente");
  btnCerrar.appendChild(icono("cerrar", 18));
  cabecera.appendChild(cabInfo);
  cabecera.appendChild(btnCerrar);
  panel.appendChild(cabecera);

  // aria-live=polite: cada respuesta nueva se anuncia sin interrumpir lo que
  // el usuario este haciendo. role=log describe el patron de conversacion.
  var conversacion = el("div", "conversacion");
  conversacion.setAttribute("role", "log");
  conversacion.setAttribute("aria-live", "polite");
  conversacion.setAttribute("aria-label", "Conversación con el asistente");
  conversacion.tabIndex = 0; // permite recorrer el historial con el teclado
  panel.appendChild(conversacion);

  var formulario = el("form", "barra");
  var entrada = el("textarea");
  entrada.rows = 1;
  entrada.placeholder = "Escribe tu pregunta…";
  entrada.setAttribute("aria-label", "Tu pregunta");
  var btnEnviar = el("button", "enviar");
  btnEnviar.type = "submit";
  btnEnviar.setAttribute("aria-label", "Enviar pregunta");
  btnEnviar.appendChild(icono("enviar", 20));
  formulario.appendChild(entrada);
  formulario.appendChild(btnEnviar);
  panel.appendChild(formulario);

  panel.appendChild(
    el(
      "div",
      "pie",
      "Respuestas basadas en la normativa institucional. Verifica siempre la fuente citada."
    )
  );

  raiz.appendChild(panel);
  document.body.appendChild(anfitrion);

  /* ---------------------------------------------------------------------------
   * 7. Abrir y cerrar
   * ------------------------------------------------------------------------ */
  var abierto = false;

  function abrirPanel() {
    abierto = true;
    panel.hidden = false;
    lanzador.hidden = true;
    lanzador.setAttribute("aria-expanded", "true");
    entrada.focus();
    if (!conversacion.childElementCount) mensajeBienvenida();
  }

  function cerrarPanel() {
    abierto = false;
    panel.hidden = true;
    lanzador.hidden = false;
    lanzador.setAttribute("aria-expanded", "false");
    // Devolver el foco al disparador: si no, el foco cae al <body> del portal
    // y quien navega por teclado se pierde.
    lanzador.focus();
  }

  lanzador.addEventListener("click", abrirPanel);
  btnCerrar.addEventListener("click", cerrarPanel);

  /* ---------------------------------------------------------------------------
   * 8. Mensajes
   * ------------------------------------------------------------------------ */
  function agregar(nodo) {
    conversacion.appendChild(nodo);
    conversacion.scrollTop = conversacion.scrollHeight;
    return nodo;
  }

  function mensajeBienvenida() {
    var m = el("div", "msg asistente");
    parrafos(
      m,
      "Hola. ¿En qué te ayudo? Respondo tus dudas sobre el prácticum con la " +
        "normativa y los documentos del curso. En cada respuesta te muestro la " +
        "página exacta de dónde lo saqué, para que puedas comprobarlo."
    );
    agregar(m);
  }

  function mensajeUsuario(texto) {
    var m = el("div", "msg usuario");
    parrafos(m, texto);
    agregar(m);
  }

  function mensajeError(texto) {
    var m = el("div", "msg error");
    parrafos(m, texto);
    agregar(m);
  }

  /** Burbuja temporal mientras la API trabaja; devuelve como quitarla. */
  function mensajeEscribiendo() {
    var m = el("div", "msg asistente");
    var p = el("span", "puntos");
    p.appendChild(el("i"));
    p.appendChild(el("i"));
    p.appendChild(el("i"));
    m.appendChild(p);
    // El texto alternativo es para el lector de pantalla, que no ve la animacion.
    var oculto = el("span", null, "Buscando en los documentos…");
    oculto.style.cssText =
      "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)";
    m.appendChild(oculto);
    agregar(m);
    return function () {
      m.remove();
    };
  }

  /**
   * Renderiza la respuesta de /preguntar.
   * Tres partes, en este orden de importancia: el texto, la salvaguarda si no
   * hay respaldo, y las citas verificables.
   */
  function mensajeRespuesta(datos) {
    var m = el("div", "msg asistente");
    parrafos(m, datos.respuesta || "(sin contenido)");

    // con_respaldo=false significa que el motor no encontro base documental.
    // Mostrarlo es un requisito del sistema: el asistente no debe aparentar
    // autoridad que no tiene, deriva a una persona.
    if (datos.con_respaldo === false) {
      m.appendChild(
        el(
          "div",
          "aviso",
          "No se encontró respaldo documental para esta consulta. " +
            "Te recomendamos confirmarla con la coordinación de prácticum."
        )
      );
    }

    var citas = Array.isArray(datos.citas) ? datos.citas : [];
    if (citas.length) m.appendChild(bloqueCitas(citas));

    agregar(m);
  }

  /** Cada cita es un boton: pulsarlo abre el documento en su pagina exacta. */
  function bloqueCitas(citas) {
    var caja = el("div", "citas");
    caja.appendChild(el("div", "citas-titulo", "De dónde lo saqué"));
    var lista = el("div", "citas-lista");

    citas.forEach(function (c) {
      var b = el("button", "cita");
      b.appendChild(icono("archivo", 15));
      b.appendChild(el("span", null, c.fuente + " · pág. " + c.pagina));
      b.type = "button";
      b.setAttribute(
        "aria-label",
        "Ver " + c.fuente + ", página " + c.pagina + ", en el visor de documentos"
      );
      b.addEventListener("click", function () {
        abrirVisor(c);
      });
      lista.appendChild(b);
    });

    caja.appendChild(lista);
    return caja;
  }

  /* ---------------------------------------------------------------------------
   * 9. Envio de la pregunta
   * ------------------------------------------------------------------------ */
  var enviando = false;
  var historial = []; // turnos de la conversacion, para resolver seguimientos

  formulario.addEventListener("submit", function (e) {
    e.preventDefault();
    preguntar();
  });

  // Enter envia, Shift+Enter salta de linea: lo que ya espera cualquiera que
  // haya usado un chat.
  entrada.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      preguntar();
    }
  });

  // El textarea crece con el contenido, hasta el tope que fija el CSS.
  entrada.addEventListener("input", function () {
    entrada.style.height = "auto";
    entrada.style.height = Math.min(entrada.scrollHeight, 110) + "px";
  });

  function preguntar() {
    var texto = entrada.value.trim();
    if (!texto || enviando) return;

    // ultimos turnos para que el asistente entienda seguimientos ("y cuantas
    // horas", "explicamelo de otra forma"), igual que la app React.
    var previos = historial.slice(-6);

    mensajeUsuario(texto);
    entrada.value = "";
    entrada.style.height = "auto";
    bloquear(true);

    var quitarEscribiendo = mensajeEscribiendo();

    api
      .preguntar(texto, previos)
      .then(function (datos) {
        quitarEscribiendo();
        mensajeRespuesta(datos);
        historial.push({ rol: "user", texto: texto });
        historial.push({ rol: "bot", texto: datos.respuesta || "" });
      })
      .catch(function (err) {
        // Un fallo de red en un widget incrustado no puede propagarse al
        // portal: se muestra aqui y la conversacion sigue viva.
        quitarEscribiendo();
        mensajeError(
          "No se pudo contactar con el asistente. " +
            detalleDeError(err) +
            " Puedes intentarlo de nuevo en unos segundos."
        );
      })
      .then(function () {
        bloquear(false);
        entrada.focus();
      });
  }

  /**
   * Traduce el fallo a algo que el estudiante entienda.
   * Cuando la peticion ni siquiera sale (servicio caido, CORS, sin conexion),
   * fetch rechaza con un TypeError cuyo texto lo pone el navegador y viene en
   * ingles: ese mensaje no se muestra, se sustituye por uno propio.
   */
  function detalleDeError(err) {
    if (err instanceof TypeError) {
      return "El servicio no está disponible en este momento.";
    }
    return err && err.message ? err.message : "Ocurrió un error inesperado.";
  }

  function bloquear(estado) {
    enviando = estado;
    btnEnviar.disabled = estado;
    entrada.disabled = estado;
    // El boton es solo icono: el estado se comunica por aria-label, no por texto,
    // para no borrar el <svg> de enviar.
    btnEnviar.setAttribute("aria-label", estado ? "Enviando…" : "Enviar pregunta");
  }

  /* ---------------------------------------------------------------------------
   * 10. Visor de documentos
   *
   * Es la pieza que hace VERIFICABLE la respuesta: el estudiante comprueba la
   * fuente sin salir del portal. La API devuelve cada pagina ya rasterizada en
   * PNG, asi que basta un <img> y no hace falta ningun lector de PDF.
   * ------------------------------------------------------------------------ */
  var visor = null; // referencias del visor abierto, o null

  function abrirVisor(cita) {
    cerrarVisor();

    var pagina = parseInt(cita.pagina, 10) || 1;
    var total = null;
    var focoPrevio = raiz.activeElement;

    var fondo = el("div", "visor-fondo");
    var caja = el("div", "visor");
    caja.setAttribute("role", "dialog");
    caja.setAttribute("aria-modal", "true");
    caja.setAttribute("aria-label", "Documento " + cita.fuente);

    // --- cabecera ---
    var cab = el("header", "cabecera");
    var info = el("div");
    info.appendChild(el("h2", null, cita.fuente));
    var etiquetaPag = el("p", null, "");
    info.appendChild(etiquetaPag);
    var cerrarV = el("button", "btn-icono");
    cerrarV.type = "button";
    cerrarV.setAttribute("aria-label", "Cerrar el documento");
    cerrarV.appendChild(icono("cerrar", 18));
    cab.appendChild(info);
    cab.appendChild(cerrarV);

    // --- cuerpo ---
    var cuerpo = el("div", "visor-cuerpo");
    var estado = el("div", "visor-estado", "Cargando página…");
    var img = el("img");
    img.hidden = true;
    cuerpo.appendChild(estado);
    cuerpo.appendChild(img);

    // --- pie ---
    var pie = el("div", "visor-pie");
    var anterior = el("button");
    anterior.type = "button";
    anterior.appendChild(icono("izquierda", 16));
    anterior.appendChild(el("span", null, "Anterior"));
    var siguiente = el("button");
    siguiente.type = "button";
    siguiente.appendChild(el("span", null, "Siguiente"));
    siguiente.appendChild(icono("derecha", 16));
    pie.appendChild(anterior);
    pie.appendChild(
      el("span", "visor-ayuda", "Usa las flechas para cambiar de página. Esc cierra.")
    );
    pie.appendChild(siguiente);

    caja.appendChild(cab);
    caja.appendChild(cuerpo);
    caja.appendChild(pie);
    fondo.appendChild(caja);
    raiz.appendChild(fondo);

    function pintar() {
      etiquetaPag.textContent =
        "Página " + pagina + (total ? " de " + total : "");
      anterior.disabled = pagina <= 1;
      siguiente.disabled = total !== null && pagina >= total;

      estado.hidden = false;
      estado.textContent = "Cargando página…";
      img.hidden = true;
      img.alt = cita.fuente + ", página " + pagina;
      img.src = api.urlPagina(cita.ref, pagina);
    }

    img.addEventListener("load", function () {
      estado.hidden = true;
      img.hidden = false;
    });
    img.addEventListener("error", function () {
      img.hidden = true;
      estado.hidden = false;
      estado.textContent = "No se pudo cargar esta página del documento.";
    });

    function ir(delta) {
      var destino = pagina + delta;
      if (destino < 1) return;
      if (total !== null && destino > total) return;
      pagina = destino;
      pintar();
    }

    anterior.addEventListener("click", function () {
      ir(-1);
    });
    siguiente.addEventListener("click", function () {
      ir(1);
    });
    cerrarV.addEventListener("click", cerrarVisor);
    // Clic en el fondo oscuro cierra; clic dentro de la caja, no.
    fondo.addEventListener("click", function (e) {
      if (e.target === fondo) cerrarVisor();
    });

    visor = { fondo: fondo, focoPrevio: focoPrevio, ir: ir, caja: caja };

    pintar();
    cerrarV.focus();

    // El total de paginas llega aparte: hasta entonces "Siguiente" queda
    // habilitado y el limite lo pone la propia API, que recorta el rango.
    api
      .infoDocumento(cita.ref)
      .then(function (i) {
        total = i.paginas;
        etiquetaPag.textContent = "Página " + pagina + " de " + total;
        siguiente.disabled = pagina >= total;
      })
      .catch(function () {
        /* sin total seguimos navegando: no es informacion critica */
      });
  }

  function cerrarVisor() {
    if (!visor) return;
    visor.fondo.remove();
    if (visor.focoPrevio && visor.focoPrevio.focus) visor.focoPrevio.focus();
    visor = null;
  }

  /* ---------------------------------------------------------------------------
   * 11. Teclado global
   *
   * Un unico listener para todo el widget. Escape cierra la capa mas interna
   * primero (visor antes que panel), que es lo que espera el usuario.
   * ------------------------------------------------------------------------ */
  raiz.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (visor) cerrarVisor();
      else if (abierto) cerrarPanel();
      return;
    }
    if (visor && e.key === "ArrowLeft") visor.ir(-1);
    if (visor && e.key === "ArrowRight") visor.ir(1);
  });
})();
