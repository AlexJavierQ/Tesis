/* ============================================================================
 * Asistente de Practicum - Widget embebible.
 *
 * Se integra en cualquier portal con UNA sola etiqueta:
 *   <script src="asistente-widget.js" data-api="http://localhost:8000"
 *           data-carrera="computacion"></script>
 *
 * NO requiere login (el endpoint /preguntar es publico para el widget).
 * NO requiere build, ni dependencias, ni CDN. Todo en un solo archivo.
 * ========================================================================= */
(function () {
  "use strict";

  // ------- 1. Configuracion (viene en atributos data-* del <script>) -------
  var script = document.currentScript;
  var CONFIG = {
    api: (script && script.dataset.api) || "http://localhost:8000",
    carrera: (script && script.dataset.carrera) || "computacion",
    curso: (script && script.dataset.curso) || null,
  };
  CONFIG.api = CONFIG.api.replace(/\/+$/, "");

  // evita cargar el widget dos veces si el <script> se incluye repetido
  if (window.__asistenteCargado) return;
  window.__asistenteCargado = true;

  // ------- 2. Estilos (van dentro del Shadow DOM para no chocar con el portal) -------
  var CSS = `
    :host { all: initial; font-family: system-ui, sans-serif; font-size: 14px; color: #e7ecf6; }
    .lanzador {
      position: fixed; right: 20px; bottom: 20px; z-index: 999999;
      padding: 12px 20px; border-radius: 30px; border: 0; cursor: pointer;
      background: linear-gradient(135deg, #5b93f0, #3f68cf);
      color: #fff; font-weight: 600; font-family: inherit;
      box-shadow: 0 4px 14px rgba(0,0,0,.4);
    }
    .panel {
      position: fixed; right: 20px; bottom: 20px; z-index: 999999;
      width: 360px; height: 520px; display: flex; flex-direction: column;
      background: #151c2b; border: 1px solid #2a3550; border-radius: 14px;
      box-shadow: 0 12px 40px rgba(0,0,0,.55); overflow: hidden;
    }
    [hidden] { display: none !important; }
    .cabecera { padding: 12px 16px; background: #1b2334; display: flex; justify-content: space-between; align-items: center; }
    .cabecera b { font-size: 15px; }
    .cerrar { background: transparent; border: 0; color: #8593ab; font-size: 20px; cursor: pointer; }
    .hilo { flex: 1; padding: 14px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
    .msg { padding: 10px 12px; border-radius: 10px; max-width: 85%; }
    .msg.usuario { align-self: flex-end; background: #4d80e6; color: #fff; }
    .msg.bot { align-self: flex-start; background: #1b2334; border: 1px solid #2a3550; }
    .cita { display: inline-block; background: rgba(110,163,251,.14); color: #6ea3fb; padding: 3px 8px; margin: 4px 4px 0 0; border-radius: 6px; font-size: 12px; }
    .aviso { margin-top: 8px; padding: 8px; background: rgba(224,185,104,.12); border-left: 3px solid #e0b968; color: #e6c684; font-size: 12px; border-radius: 4px; }
    .barra { display: flex; gap: 6px; padding: 10px; border-top: 1px solid #2a3550; }
    .barra textarea { flex: 1; resize: none; padding: 8px 12px; border-radius: 8px; border: 1px solid #2a3550; background: #1b2334; color: #e7ecf6; font-family: inherit; font-size: 14px; height: 40px; }
    .barra button { padding: 8px 16px; border: 0; border-radius: 8px; background: #5b93f0; color: #fff; font-weight: 600; cursor: pointer; }
    .error { color: #f3a79d; font-size: 12px; }
  `;

  // ------- 3. Cliente HTTP (una sola llamada: /preguntar) -------
  function preguntarAPI(pregunta) {
    return fetch(CONFIG.api + "/preguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pregunta: pregunta,
        carrera: CONFIG.carrera,
        curso: CONFIG.curso,
      }),
    }).then(function (r) {
      if (!r.ok) throw new Error("La API respondio " + r.status);
      return r.json();
    });
  }

  // ------- 4. Shadow DOM: aisla nuestro CSS del portal anfitrion -------
  var anfitrion = document.createElement("div");
  var raiz = anfitrion.attachShadow({ mode: "open" });
  var hoja = document.createElement("style");
  hoja.textContent = CSS;
  raiz.appendChild(hoja);

  // ------- 5. Construccion de la UI -------
  // helper: crea un nodo con clase y texto
  function el(tag, clase, texto) {
    var n = document.createElement(tag);
    if (clase) n.className = clase;
    if (texto != null) n.textContent = texto;
    return n;
  }

  var lanzador = el("button", "lanzador", "💬 Asistente de Practicum");
  raiz.appendChild(lanzador);

  var panel = el("div", "panel");
  panel.hidden = true;

  var cabecera = el("div", "cabecera");
  cabecera.appendChild(el("b", null, "Asistente de Practicum"));
  var btnCerrar = el("button", "cerrar", "×");
  cabecera.appendChild(btnCerrar);
  panel.appendChild(cabecera);

  var hilo = el("div", "hilo");
  panel.appendChild(hilo);

  var barra = el("form", "barra");
  var entrada = el("textarea");
  entrada.placeholder = "Escribe tu pregunta...";
  var btnEnviar = el("button", null, "Enviar");
  btnEnviar.type = "submit";
  barra.appendChild(entrada);
  barra.appendChild(btnEnviar);
  panel.appendChild(barra);

  raiz.appendChild(panel);
  document.body.appendChild(anfitrion);

  // ------- 6. Comportamiento -------
  function agregarMsg(clase, texto, citas, sinRespaldo) {
    var m = el("div", "msg " + clase);
    // OJO: usamos textContent (no innerHTML) porque el texto viene del LLM
    // y puede contener caracteres HTML que serian interpretados.
    m.appendChild(el("p", null, texto));
    if (sinRespaldo) {
      m.appendChild(el("div", "aviso",
        "Sin respaldo documental: te recomendamos consultar con la coordinacion."));
    }
    if (citas && citas.length) {
      var caja = el("div");
      citas.forEach(function (c) {
        caja.appendChild(el("span", "cita", c.fuente + " · pag. " + c.pagina));
      });
      m.appendChild(caja);
    }
    hilo.appendChild(m);
    hilo.scrollTop = hilo.scrollHeight;
  }

  lanzador.addEventListener("click", function () {
    panel.hidden = false;
    lanzador.hidden = true;
    if (!hilo.childElementCount) {
      agregarMsg("bot", "Hola. ¿En que te ayudo? Pregunta sobre el Practicum.");
    }
    entrada.focus();
  });

  btnCerrar.addEventListener("click", function () {
    panel.hidden = true;
    lanzador.hidden = false;
  });

  barra.addEventListener("submit", function (e) {
    e.preventDefault();
    var q = entrada.value.trim();
    if (!q) return;
    agregarMsg("usuario", q);
    entrada.value = "";
    btnEnviar.disabled = true;
    preguntarAPI(q)
      .then(function (r) {
        agregarMsg("bot", r.respuesta, r.citas, !r.con_respaldo);
      })
      .catch(function (err) {
        agregarMsg("bot", "No pude contactar la API. " + err.message);
      })
      .finally(function () { btnEnviar.disabled = false; entrada.focus(); });
  });
})();
