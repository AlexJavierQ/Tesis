# -*- coding: utf-8 -*-
"""
Motor RAG (C2) — ORQUESTADOR. No conoce las herramientas concretas:
habla con los adaptadores (vectorstore, llm). Así cambiar una herramienta
no afecta esta lógica.

Alcances (scope):
  "<carrera>|global"          -> reglamentos de la carrera (coordinacion)
  "<carrera>|curso:<curso>"   -> documentos de un curso (docente)
"""
import os
import vectorstore
import llm

BASE = os.path.dirname(__file__)
DOCS = os.path.join(BASE, "docs")
GEMINI_MODEL = llm.MODEL          # re-exporta para la API (/salud)
TOP_K = 5
THRESHOLD = 0.65


# ---------- estructura carrera / curso ----------
def carreras():
    if not os.path.isdir(DOCS):
        return []
    return sorted(d for d in os.listdir(DOCS) if os.path.isdir(os.path.join(DOCS, d)))


def cursos(carrera):
    cdir = os.path.join(DOCS, carrera, "cursos")
    if not os.path.isdir(cdir):
        return []
    return sorted(d for d in os.listdir(cdir) if os.path.isdir(os.path.join(cdir, d)))


def folder_global(carrera):
    return os.path.join(DOCS, carrera, "global")


def folder_curso(carrera, curso):
    return os.path.join(DOCS, carrera, "cursos", curso)


def scope_global(carrera):
    return f"{carrera}|global"


def scope_curso(carrera, curso):
    return f"{carrera}|curso:{curso}"


def scopes_for(carrera, curso=None):
    s = [scope_global(carrera)]
    if curso:
        s.append(scope_curso(carrera, curso))
    return s


def folder_de(scope):
    carrera, resto = scope.split("|", 1)
    if resto == "global":
        return folder_global(carrera)
    return folder_curso(carrera, resto.split("curso:", 1)[1])


# ---------- recuperar + responder ----------
def retrieve(question, scopes=None, k=TOP_K):
    where = {"scope": {"$in": scopes}} if scopes else None
    hits = []
    for doc, meta, dist in vectorstore.query(question, k, where=where):
        hits.append({"texto": doc, "fuente": meta.get("fuente", "?"),
                     "pagina": meta.get("pagina", "?"), "path": meta.get("path", ""),
                     "scope": meta.get("scope", ""), "distancia": dist})
    return hits


def _build_prompt(question, hits):
    bloques = [f"[Fuente: {h['fuente']}, pag. {h['pagina']}]\n{h['texto']}" for h in hits]
    return f"""Eres el asistente de Practicum (practicas preprofesionales) de la UTPL.
Responde UNICAMENTE con la informacion del contexto de abajo.
Si la respuesta no esta en el contexto, responde exactamente:
"No tengo informacion oficial sobre eso. Te recomiendo consultar con la coordinacion."
Responde en espanol, claro y breve. Al final cita la fuente entre parentesis asi: (Fuente: archivo, pag. X).

Contexto:
{chr(10).join(bloques)}

Pregunta: {question}
Respuesta:"""


def answer(question, api_key=None, scopes=None):
    hits = retrieve(question, scopes=scopes)
    if not hits:
        return {"respuesta": "Aun no hay documentos para responder esto.",
                "fuentes": [], "citas": [], "con_respaldo": False}
    if min(h["distancia"] for h in hits) > THRESHOLD:
        return {"respuesta": "No tengo informacion oficial sobre eso. Te recomiendo consultar con la coordinacion.",
                "fuentes": [], "citas": [], "con_respaldo": False}

    usados = [h for h in hits if h["distancia"] <= THRESHOLD]
    vistos, citas = set(), []
    for h in usados:
        key = (h["fuente"], h["pagina"])
        if key not in vistos:
            vistos.add(key)
            citas.append({"fuente": h["fuente"], "pagina": h["pagina"], "path": h["path"]})
    fuentes_str = [f"{c['fuente']} (pag. {c['pagina']})" for c in citas]
    ctx_breve = "\n\n".join(f"- {h['texto']}  ({h['fuente']}, pag. {h['pagina']})" for h in usados[:2])

    texto = llm.generate(_build_prompt(question, usados), api_key=api_key)
    if not texto:
        # sin API key o el modelo fallo -> mostramos lo recuperado (no se rompe)
        texto = "(Según los documentos oficiales:)\n\n" + ctx_breve
    else:
        low = texto.lower()
        # si el modelo NO encontro la respuesta en el contexto, no mostramos citas
        # (coherencia: nada de "no tengo informacion" + fuentes citadas)
        if "coordinaci" in low and ("no tengo" in low or "no hay informaci" in low or "no cuento" in low):
            return {"respuesta": texto, "fuentes": [], "citas": [], "con_respaldo": False}
    return {"respuesta": texto, "fuentes": fuentes_str, "citas": citas, "con_respaldo": True}
