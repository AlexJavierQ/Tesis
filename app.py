# -*- coding: utf-8 -*-
"""
Front demo (C3): estudiante (chat) + docente (cursos + metricas de su aula) +
coordinacion (reglamentos + metricas de la carrera). Cliente del nucleo.
Uso:  streamlit run app.py
"""
import os
# carga proveedor LLM + keys desde secrets.toml ANTES de importar el motor
try:
    import tomllib
    _sec = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(_sec):
        with open(_sec, "rb") as _f:
            for _k, _v in tomllib.load(_f).items():
                if _k in ("LLM_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY"):
                    os.environ.setdefault(_k, str(_v))
except Exception:
    pass

import re
import glob
import sqlite3
import datetime as dt
from collections import Counter
import numpy as np
import streamlit as st
import pandas as pd
import rag
import ingest
import pdfreader
import embeddings as emb
import llm

BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, "consultas.db")
PASS_DOCENTE = "docente2026"
PASS_COORD = "utpl2026"
SUGERIDAS = ["¿Cuántas horas necesito?", "¿Cuál es el plazo del informe?",
             "¿Qué formato uso para el informe?", "¿Cuál es la nota mínima?"]


def get_api_key():
    return os.environ.get("GEMINI_API_KEY") or None


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
    st.session_state.ver_doc = {"path": path, "fuente": fuente, "pagina": int(pagina)}


# ---------------- registro anonimo (con ambito = donde se pregunto) ----------------
def _conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("CREATE TABLE IF NOT EXISTS consultas "
              "(ts TEXT, pregunta TEXT, respondida INTEGER, fuentes TEXT, ambito TEXT)")
    cols = [r[1] for r in c.execute("PRAGMA table_info(consultas)").fetchall()]
    if "ambito" not in cols:
        c.execute("ALTER TABLE consultas ADD COLUMN ambito TEXT")
    return c


def log_consulta(p, ok, fu, ambito):
    c = _conn()
    c.execute("INSERT INTO consultas VALUES (?,?,?,?,?)",
              (dt.datetime.now().strftime("%Y-%m-%d %H:%M"), p, int(ok), " | ".join(fu), ambito))
    c.commit(); c.close()


def consultas(prefix=None, exact=None):
    c = _conn()
    if exact:
        filas = c.execute("SELECT ts,pregunta,respondida,ambito FROM consultas WHERE ambito=? ORDER BY ts DESC", (exact,)).fetchall()
    elif prefix:
        filas = c.execute("SELECT ts,pregunta,respondida,ambito FROM consultas WHERE ambito LIKE ? ORDER BY ts DESC", (prefix + "%",)).fetchall()
    else:
        filas = c.execute("SELECT ts,pregunta,respondida,ambito FROM consultas ORDER BY ts DESC").fetchall()
    c.close()
    return filas


# ---------------- agrupar preguntas por SIGNIFICADO (no por texto exacto) ----------------
@st.cache_data(show_spinner=False)
def agrupar_temas(preguntas, umbral=0.68):
    cnt = Counter(p.strip() for p in preguntas)
    unicas = [u for u in cnt if u]
    if not unicas:
        return []
    vecs = emb.embed(unicas)                      # vectores normalizados
    clusters = []
    for i in range(len(unicas)):
        mejor, sim_max = None, -1.0
        for cl in clusters:
            sim = float(np.dot(vecs[i], vecs[cl["rep"]]))
            if sim > sim_max:
                sim_max, mejor = sim, cl
        if mejor and sim_max >= umbral:
            mejor["miembros"].append(i); mejor["n"] += cnt[unicas[i]]
        else:
            clusters.append({"rep": i, "miembros": [i], "n": cnt[unicas[i]]})
    out = []
    for cl in clusters:
        rep = max(cl["miembros"], key=lambda idx: cnt[unicas[idx]])
        out.append({"tema": unicas[rep], "n": cl["n"], "variantes": len(cl["miembros"])})
    return sorted(out, key=lambda x: -x["n"])


def render_metricas(filas):
    total = len(filas); resp = sum(f[2] for f in filas)
    a, b, c = st.columns(3)
    a.metric("Consultas", total); b.metric("Con respaldo", resp)
    c.metric("% respaldo", f"{(100*resp/total):.0f}%" if total else "—")
    if not filas:
        st.info("Aún no hay consultas en este ámbito."); return
    temas = agrupar_temas(tuple(f[1] for f in filas))
    st.markdown("**🔁 Temas más consultados** (agrupados por significado, no por texto exacto)")
    df = pd.DataFrame({"tema": [t["tema"][:40] for t in temas[:8]],
                       "veces": [t["n"] for t in temas[:8]]}).set_index("tema")
    st.bar_chart(df)
    with st.expander("¿Cómo se agrupan los temas?"):
        st.caption("Preguntas que significan lo mismo se juntan aunque estén escritas distinto.")
        for t in temas[:8]:
            st.write(f"• **{t['tema']}** — {t['n']} consultas en {t['variantes']} forma(s) distinta(s)")
    sin = list(dict.fromkeys(f[1] for f in filas if not f[2]))
    st.markdown("**❓ Preguntas sin respaldo** (vacíos a cubrir)")
    for s in sin[:8]:
        st.write("• " + s)
    with st.expander("Ver consultas individuales (anónimas)"):
        st.dataframe({"Fecha": [f[0] for f in filas], "Pregunta": [f[1] for f in filas],
                      "Respaldo": ["Sí" if f[2] else "No" for f in filas]},
                     use_container_width=True, hide_index=True)


# ---------------- ayuda ----------------
AYUDA = ("Soy el asistente de Prácticum. Respondo con los **documentos oficiales**.\n\n"
         "Por ejemplo: *¿Cuántas horas necesito?*, *¿Cuál es el plazo del informe?*, "
         "*¿Qué formato uso?*, *¿Cuál es la nota mínima?*\n\n"
         "Si pregunto algo que no está en los documentos, te derivo a la coordinación.")
PATRONES = [r"\bhola\b", r"\bbuen[oa]s\b", r"\bayuda\b", r"puedo? pregunt", r"qu[eé] pregunt",
            r"qu[eé] puedes? (hacer|responder|consultar)", r"c[oó]mo funciona", r"qui[eé]n eres"]


def responder(q, api_key, scopes):
    if any(re.search(p, q.lower()) for p in PATRONES):
        return {"respuesta": AYUDA, "fuentes": [], "citas": [], "con_respaldo": True}
    return rag.answer(q, api_key, scopes=scopes)


# ---------------- UI ----------------
st.set_page_config(page_title="Asistente de Practicum", page_icon="🎓", layout="centered")
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.topbar {position: sticky; top: 0; z-index: 9999; background:#1F3864; color:#fff;
 padding:12px 22px; font-size:20px; font-weight:700; border-radius:0 0 12px 12px;
 margin:-1rem -1rem 1rem -1rem; box-shadow:0 2px 8px rgba(0,0,0,.15);}
.topbar small {font-weight:400; font-size:13px; opacity:.85;}
</style>
<div class="topbar">🎓 Asistente de Prácticum &nbsp;<small>UTPL</small></div>
""", unsafe_allow_html=True)

api_key = get_api_key()
if "ver_doc" not in st.session_state:
    st.session_state.ver_doc = None


@st.dialog("📄 Documento", width="large")
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
    if a.button("◀ Anterior", disabled=pag <= 1, key="mp"):
        st.session_state.ver_doc["pagina"] = pag - 1; st.rerun()
    if b.button("Cerrar", key="mc"):
        st.session_state.ver_doc = None; st.rerun()
    if c.button("Siguiente ▶", disabled=pag >= total, key="mn"):
        st.session_state.ver_doc["pagina"] = pag + 1; st.rerun()


with st.sidebar:
    st.markdown("### Menú")
    carrs = rag.carreras() or ["computacion"]
    carrera = st.selectbox("Carrera", carrs)
    rol = st.radio("Entrar como:", ["Estudiante", "Docente", "Coordinacion"])
    st.caption(f"⚙️ Motor: {llm.PROVIDER} · {llm.MODEL}")

# al cambiar de rol, cierra el visor (evita que se abra solo)
if st.session_state.get("_prev_rol") != rol:
    st.session_state.ver_doc = None
    st.session_state._prev_rol = rol

if st.session_state.ver_doc:
    modal_doc()


def pintar(m, idx):
    with st.chat_message(m["rol"], avatar=("🎓" if m["rol"] == "user" else "🤖")):
        st.markdown(m["txt"])
        if m["rol"] == "assistant":
            if not m.get("con_respaldo", True):
                st.info("Sin respaldo documental: deriva a la coordinación.")
            cs = m.get("citas", [])
            cols = st.columns(max(1, len(cs)))
            for j, c in enumerate(cs):
                if cols[j].button(f"📄 {c['fuente']} · p.{c['pagina']}", key=f"c{idx}_{j}", help="Ver la página"):
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
    st.caption("Pregunta sobre trámites, horas, plazos y formatos. Respondo solo con los documentos.")
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
        st.session_state.hist.append({"rol": "user", "txt": q})
        with st.spinner("Buscando en los documentos..."):
            r = responder(q, api_key, scopes)
        st.session_state.hist.append({"rol": "assistant", "txt": r["respuesta"],
                                      "citas": r.get("citas", []), "con_respaldo": r.get("con_respaldo", True)})
        log_consulta(q, r.get("con_respaldo", True), r.get("fuentes", []), scopes[-1])
        st.rerun()

# ===================== DOCENTE =====================
elif rol == "Docente":
    with st.sidebar:
        ok = st.text_input("Contraseña docente", type="password") == PASS_DOCENTE
    if not ok:
        st.warning("Ingresa la contraseña de docente. (demo: docente2026)"); st.stop()
    st.subheader(f"👩‍🏫 Docente · {carrera}")
    nuevo = st.text_input("Crear nuevo curso (nombre)")
    if st.button("➕ Crear curso") and nuevo.strip():
        os.makedirs(rag.folder_curso(carrera, nuevo.strip()), exist_ok=True)
        st.success(f"Curso '{nuevo}' creado."); st.rerun()
    cs = rag.cursos(carrera)
    if not cs:
        st.info("Aún no hay cursos. Crea uno arriba."); st.stop()
    curso = st.selectbox("Curso:", cs)
    scope = rag.scope_curso(carrera, curso)
    tab1, tab2 = st.tabs(["📄 Documentos", "📊 Métricas de mi aula"])
    with tab1:
        st.caption("Estos documentos solo afectan al chatbot de este curso.")
        sub = st.file_uploader(f"Subir PDF a '{curso}'", type="pdf")
        if sub and st.button("📤 Subir e indexar"):
            path = guardar_subida(sub, scope)
            with st.spinner("Indexando..."):
                n = ingest.add_pdf(path, scope)
            st.success(f"'{sub.name}' indexado ({n} fragmentos)."); st.rerun()
        for nombre, path in docs_de(scope):
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.write("• " + nombre)
            if c2.button("👁", key="v" + nombre):
                abrir(path, nombre, 1); st.rerun()
            if c3.button("🗑", key="x" + nombre):
                ingest.remove_doc(nombre, scope); os.remove(path); st.rerun()
    with tab2:
        st.caption(f"🔒 Anónimo · solo las consultas hechas en el curso '{curso}'.")
        render_metricas(consultas(exact=scope))

# ===================== COORDINACION =====================
else:
    with st.sidebar:
        ok = st.text_input("Contraseña coordinación", type="password") == PASS_COORD
    if not ok:
        st.warning("Ingresa la contraseña de coordinación. (demo: utpl2026)"); st.stop()
    st.subheader(f"🏛️ Coordinación · {carrera}")
    tab1, tab2 = st.tabs(["📄 Reglamentos", "📊 Métricas"])
    with tab1:
        st.caption("Estos documentos afectan a TODOS los chats de la carrera.")
        scope = rag.scope_global(carrera)
        sub = st.file_uploader("Subir reglamento", type="pdf")
        if sub and st.button("📤 Subir e indexar"):
            path = guardar_subida(sub, scope)
            with st.spinner("Indexando..."):
                n = ingest.add_pdf(path, scope)
            st.success(f"'{sub.name}' indexado ({n} fragmentos)."); st.rerun()
        for nombre, path in docs_de(scope):
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.write("• " + nombre)
            if c2.button("👁", key="vg" + nombre):
                abrir(path, nombre, 1); st.rerun()
            if c3.button("🗑", key="xg" + nombre):
                ingest.remove_doc(nombre, scope); os.remove(path); st.rerun()
    with tab2:
        st.caption(f"🔒 Anónimo · todas las consultas de la carrera '{carrera}'.")
        render_metricas(consultas(prefix=carrera + "|"))
