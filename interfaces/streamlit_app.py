# -*- coding: utf-8 -*-
"""
Front demo (C3): estudiante (chat) + docente (cursos + metricas de su aula) +
coordinacion (reglamentos + metricas de la carrera). Cliente del nucleo.
Uso:  streamlit run interfaces/streamlit_app.py
"""
import os
# permite ejecutar este archivo directamente: agrega la raiz del proyecto al path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import config          # carga proveedor LLM + keys ANTES de importar el motor  # noqa: F401

import re
import glob
import streamlit as st
import pandas as pd
from nucleo import rag, ingest, pdfreader, metricas, llm

BASE = os.path.dirname(__file__)
PASS_DOCENTE = "docente2026"
PASS_COORD = "utpl2026"
SUGERIDAS = ["¿Cuántas horas necesito?", "¿Cuál es el plazo del informe?",
             "¿Qué formato uso para el informe?", "¿Cuál es la nota mínima?"]


def get_api_key():
    return config.key_activa()


def docs_de(scope):
    folder = rag.folder_de(scope)
    return sorted((os.path.basename(p), os.path.abspath(p)) for p in glob.glob(os.path.join(folder, "*.pdf")))


def guardar_subida(uploaded, scope):
    folder = rag.folder_de(scope)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, uploaded.name)
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    return path


@st.cache_data(show_spinner=False)
def render(path, pagina):
    return pdfreader.render_png(path, pagina) if os.path.exists(path) else None


def abrir(path, fuente, pagina=1):
    # la ingesta guarda rutas relativas a docs/; las absolutas vienen de listados locales
    if path and not os.path.isabs(path):
        path = os.path.join(rag.DOCS, path)
    st.session_state.ver_doc = {"path": path, "fuente": fuente, "pagina": int(pagina)}


# ---------------- registro anonimo (logica compartida con la API) ----------------
log_consulta = metricas.registrar
consultas = metricas.listar


@st.cache_data(show_spinner=False)
def agrupar_temas(preguntas, umbral=0.68):
    return metricas.agrupar_temas(preguntas, umbral)


def render_metricas(filas):
    total = len(filas); resp = sum(f[2] for f in filas)
    a, b, c = st.columns(3)
    a.metric("Consultas", total); b.metric("Con respaldo", resp)
    c.metric("% respaldo", f"{(100*resp/total):.0f}%" if total else "n/d")
    if not filas:
        st.info("Aún no hay consultas en este ámbito."); return
    temas = agrupar_temas(tuple(f[1] for f in filas))
    st.markdown("**Temas más consultados** (agrupados por significado, no por texto exacto)")
    df = pd.DataFrame({"tema": [t["tema"][:40] for t in temas[:8]],
                       "veces": [t["n"] for t in temas[:8]]}).set_index("tema")
    st.bar_chart(df)
    with st.expander("¿Cómo se agrupan los temas?"):
        st.caption("Preguntas que significan lo mismo se juntan aunque estén escritas distinto.")
        for t in temas[:8]:
            st.write(f"• **{t['tema']}**: {t['n']} consultas en {t['variantes']} forma(s) distinta(s)")
    sin = list(dict.fromkeys(f[1] for f in filas if not f[2]))
    st.markdown("**Preguntas sin respaldo** (vacíos a cubrir)")
    for s in sin[:8]:
        st.write("• " + s)
    with st.expander("Ver consultas individuales (anónimas)"):
        st.dataframe({"Fecha": [f[0] for f in filas], "Pregunta": [f[1] for f in filas],
                      "Respaldo": ["Sí" if f[2] else "No" for f in filas]},
                     use_container_width=True, hide_index=True)


# Los saludos, la cortesia y los seguimientos ("y cuantas horas", "explicamelo
# de otra forma") los resuelve el nucleo (rag.answer), igual que en la API, para
# que las tres propuestas se comporten igual.
def responder(q, api_key, scopes, historial=None):
    return rag.answer(q, api_key, scopes=scopes, historial=historial)


# ---------------- UI ----------------
# Icono emblematico de la marca (la "chispa"), el mismo de las otras propuestas.
CHISPA = ('<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" '
          'stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
          '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 '
          '9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .962 0L14.063 8.5A2 2 0 0 0 '
          '15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 '
          '6.135a.5.5 0 0 1-.962 0z"/></svg>')

st.set_page_config(page_title="Asistente de Practicum", layout="centered")
st.markdown(f"""
<style>
#MainMenu, footer {{visibility: hidden;}}
.topbar {{position: sticky; top: 0; z-index: 9999;
 background: linear-gradient(135deg,#5b93f0,#3f68cf); color:#fff;
 display:flex; align-items:center; gap:11px;
 padding:13px 22px; border-radius:0 0 14px 14px;
 margin:-1rem -1rem 1rem -1rem; box-shadow:0 2px 12px rgba(0,0,0,.35);}}
.topbar b {{font-size:19px; font-weight:700;}}
.topbar small {{font-weight:400; font-size:12px; opacity:.85;}}
</style>
<div class="topbar">{CHISPA.format(s=24, c='#fff')}
 <b>Asistente de Prácticum</b><small>UTPL · Computación</small></div>
""", unsafe_allow_html=True)

# avatares como data-URI del mismo icono (Streamlit no acepta SVG inline en el avatar)
import base64
def _avatar(color):
    svg = CHISPA.format(s=22, c=color)
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
AVATAR_BOT = _avatar("#6ea3fb")
AVATAR_USER = _avatar("#b3bfd2")

api_key = get_api_key()
if "ver_doc" not in st.session_state:
    st.session_state.ver_doc = None


@st.dialog("Documento", width="large")
def modal_doc():
    vd = st.session_state.ver_doc
    if not vd or not os.path.exists(vd["path"]):
        st.warning("No encuentro el archivo."); return
    total = pdfreader.num_paginas(vd["path"])
    pag = max(1, min(vd["pagina"], total))
    st.markdown(f"**{vd['fuente']}** · pág. {pag}/{total}")
    img = render(vd["path"], pag)
    if img:
        st.image(img, use_container_width=True)
    a, b, c = st.columns(3)
    if a.button("Anterior", disabled=pag <= 1, key="mp", use_container_width=True):
        st.session_state.ver_doc["pagina"] = pag - 1; st.rerun()
    if b.button("Cerrar", key="mc", use_container_width=True):
        st.session_state.ver_doc = None; st.rerun()
    if c.button("Siguiente", disabled=pag >= total, key="mn", use_container_width=True):
        st.session_state.ver_doc["pagina"] = pag + 1; st.rerun()


with st.sidebar:
    st.markdown("### Menú")
    carrs = rag.carreras() or ["computacion"]
    carrera = st.selectbox("Carrera", carrs)
    rol = st.radio("Entrar como:", ["Estudiante", "Docente", "Coordinacion"])
    st.caption(f"Motor: {llm.PROVIDER} · {llm.MODEL}")

# al cambiar de rol, cierra el visor (evita que se abra solo)
if st.session_state.get("_prev_rol") != rol:
    st.session_state.ver_doc = None
    st.session_state._prev_rol = rol

if st.session_state.ver_doc:
    modal_doc()


def pintar(m, idx):
    with st.chat_message(m["rol"], avatar=(AVATAR_USER if m["rol"] == "user" else AVATAR_BOT)):
        st.markdown(m["txt"])
        if m["rol"] == "assistant":
            if not m.get("con_respaldo", True):
                st.info("Sin respaldo documental: deriva a la coordinación.")
            cs = m.get("citas", [])
            cols = st.columns(max(1, len(cs)))
            for j, c in enumerate(cs):
                if cols[j].button(f"{c['fuente']} · p.{c['pagina']}", key=f"c{idx}_{j}", help="Ver la página"):
                    abrir(c["path"], c["fuente"], c["pagina"]); st.rerun()


# ===================== ESTUDIANTE =====================
if rol == "Estudiante":
    with st.sidebar:
        cs = rag.cursos(carrera)
        sel = st.selectbox("¿Sobre qué consultas?", ["General (reglamentos)"] + [f"Curso: {c}" for c in cs])
        if sel.startswith("General"):
            scopes = rag.scopes_for(carrera)
        else:
            scopes = rag.scopes_for(carrera, sel.split("Curso: ", 1)[1])

    if "hist" not in st.session_state:
        st.session_state.hist = []
    st.caption("Pregunta sobre trámites, horas, plazos y formatos.")
    for i, m in enumerate(st.session_state.hist):
        pintar(m, i)
    if not st.session_state.hist:
        st.write("**Prueba con una de estas:**")
        cc = st.columns(2)
        for i, s in enumerate(SUGERIDAS):
            if cc[i % 2].button(s, key=f"sug{i}", use_container_width=True):
                st.session_state.pending_q = s; st.rerun()

    preg = st.chat_input("Escribe tu consulta...")
    q = preg or st.session_state.pop("pending_q", None)
    if q:
        historial = list(st.session_state.hist)   # turnos previos (sin la pregunta actual)
        st.session_state.hist.append({"rol": "user", "txt": q})
        with st.spinner("Buscando en los documentos..."):
            r = responder(q, api_key, scopes, historial=historial)
        st.session_state.hist.append({"rol": "assistant", "txt": r["respuesta"],
                                      "citas": r.get("citas", []), "con_respaldo": r.get("con_respaldo", True)})
        if not r.get("social"):   # saludos y cortesia no cuentan como consultas
            log_consulta(q, r.get("con_respaldo", True), r.get("fuentes", []), scopes[-1])
        st.rerun()

# ===================== DOCENTE =====================
elif rol == "Docente":
    with st.sidebar:
        ok = st.text_input("Contraseña docente", type="password") == PASS_DOCENTE
    if not ok:
        st.warning("Ingresa la contraseña de docente. (docente2026)"); st.stop()
    st.subheader(f"Docente · {carrera}")
    nuevo = st.text_input("Crear nuevo curso (nombre)")
    if st.button("Crear curso") and nuevo.strip():
        os.makedirs(rag.folder_curso(carrera, nuevo.strip()), exist_ok=True)
        st.success(f"Curso '{nuevo}' creado."); st.rerun()
    cs = rag.cursos(carrera)
    if not cs:
        st.info("Aún no hay cursos. Crea uno arriba."); st.stop()
    curso = st.selectbox("Curso:", cs)
    scope = rag.scope_curso(carrera, curso)
    tab1, tab2 = st.tabs(["Documentos", "Métricas del aula"])
    with tab1:
        st.caption("Estos documentos solo afectan al chatbot de este curso.")
        sub = st.file_uploader(f"Subir PDF a '{curso}'", type="pdf")
        if sub and st.button("Subir e indexar"):
            path = guardar_subida(sub, scope)
            with st.spinner("Indexando..."):
                n = ingest.add_pdf(path, scope)
            st.success(f"'{sub.name}' indexado ({n} fragmentos)."); st.rerun()
        for nombre, path in docs_de(scope):
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.write("• " + nombre)
            if c2.button("Ver", key="v" + nombre):
                abrir(path, nombre, 1); st.rerun()
            if c3.button("Quitar", key="x" + nombre):
                ingest.remove_doc(nombre, scope); os.remove(path); st.rerun()
    with tab2:
        st.caption(f"Anónimo · solo las consultas hechas en el curso '{curso}'.")
        render_metricas(consultas(exact=scope))

# ===================== COORDINACION =====================
else:
    with st.sidebar:
        ok = st.text_input("Contraseña coordinación", type="password") == PASS_COORD
    if not ok:
        st.warning("Ingresa la contraseña de coordinación.(utpl2026)"); st.stop()
    st.subheader(f"Coordinación · {carrera}")
    tab1, tab2 = st.tabs(["Reglamentos", "Métricas"])
    with tab1:
        st.caption("Estos documentos afectan a TODOS los chats de la carrera.")
        scope = rag.scope_global(carrera)
        sub = st.file_uploader("Subir reglamento", type="pdf")
        if sub and st.button("Subir e indexar"):
            path = guardar_subida(sub, scope)
            with st.spinner("Indexando..."):
                n = ingest.add_pdf(path, scope)
            st.success(f"'{sub.name}' indexado ({n} fragmentos)."); st.rerun()
        for nombre, path in docs_de(scope):
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.write("• " + nombre)
            if c2.button("Ver", key="vg" + nombre):
                abrir(path, nombre, 1); st.rerun()
            if c3.button("Quitar", key="xg" + nombre):
                ingest.remove_doc(nombre, scope); os.remove(path); st.rerun()
    with tab2:
        st.caption(f"Anónimo · todas las consultas de la carrera '{carrera}'.")
        render_metricas(consultas(prefix=carrera + "|"))
