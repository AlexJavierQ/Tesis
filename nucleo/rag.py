# -*- coding: utf-8 -*-
"""
ORQUESTADOR RAG.

RAG = Retrieval Augmented Generation.:
  1. Buscar en los documentos los fragmentos mas relevantes para la pregunta.
  2. Meter esos fragmentos como CONTEXTO en el prompt del LLM.
  3. Pedirle al LLM que responda usando SOLO ese contexto.

Ambitos (scope): etiqueta que distingue de que documentos se puede leer.
  "<carrera>|global"          -> reglamentos generales de la carrera
  "<carrera>|curso:<curso>"   -> documentos de un curso especifico
"""
import os
from nucleo import vectorstore, llm

BASE = os.path.dirname(__file__)
DOCS = os.path.join(os.path.dirname(BASE), "datos", "docs")

TOP_K = 8          # fragmentos a recuperar
UMBRAL = 0.65      # si el mas cercano supera esta distancia, NO se responde
MAX_CITAS = 3      # citas mostradas al usuario

ABSTENCION = ("No tengo informacion oficial sobre eso. "
              "Te recomiendo consultar con la coordinacion.")

AYUDA = ("Soy el asistente de Practicum de la UTPL. Respondo con los "
         "reglamentos y silabos oficiales. Preguntame por ejemplo: cuantas "
         "horas necesitas, cual es el plazo del informe, que formato usar, "
         "cual es la nota minima o los prerrequisitos. Si algo no esta en "
         "los documentos, te derivo a la coordinacion.")


def _mensaje_social(pregunta):
    """
    Detecta saludos, cortesias y pedidos de ayuda. Devuelve la respuesta o None.
    Se resuelve sin buscar en el corpus ni llamar al LLM.
    """
    q = pregunta.lower().strip(" ?!.,¿¡")
    if q in ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
             "hey", "que tal", "saludos"):
        return "Hola. " + AYUDA
    if q in ("gracias", "muchas gracias", "ok", "vale", "perfecto",
             "entendido", "listo", "genial"):
        return "Con gusto. Si te queda otra duda sobre el Practicum, aqui estoy."
    if any(t in q for t in ("ayuda", "que puedo pregunt", "que puedes",
                            "como funcionas", "quien eres", "para que sirves",
                            "help")):
        return AYUDA
    return None


# ---------- estructura de carpetas ----------
def carreras():
    """Lista las carreras que tienen documentos (subcarpetas de datos/docs/)."""
    if not os.path.isdir(DOCS):
        return []
    return sorted(d for d in os.listdir(DOCS)
                  if os.path.isdir(os.path.join(DOCS, d)))


def cursos(carrera):
    """Lista los cursos de una carrera (subcarpetas de cursos/)."""
    cdir = os.path.join(DOCS, carrera, "cursos")
    if not os.path.isdir(cdir):
        return []
    return sorted(d for d in os.listdir(cdir)
                  if os.path.isdir(os.path.join(cdir, d)))


def carpeta_global(carrera):
    return os.path.join(DOCS, carrera, "global")


def carpeta_curso(carrera, curso):
    return os.path.join(DOCS, carrera, "cursos", curso)


def scopes_de(carrera, curso=None):
    """Ambitos donde buscar: siempre el global, y opcionalmente el del curso."""
    s = [f"{carrera}|global"]
    if curso:
        s.append(f"{carrera}|curso:{curso}")
    return s


# ---------- flujo principal ----------
def _prompt(pregunta, hits):
    """Construye el prompt con el contexto recuperado."""
    contexto = "\n\n".join(
        f"[Fuente: {h['meta']['fuente']}, pag. {h['meta']['pagina']}]\n{h['texto']}"
        for h in hits
    )
    return f"""Eres el asistente de Practicum de la UTPL. Responde SOLO usando
el contexto que sigue. Si el dato exacto no esta en el contexto, contesta
EXACTAMENTE esto y nada mas:
{ABSTENCION}

Si tienes la respuesta, redactala breve y clara en espanol, y al final agrega
(Fuente: archivo, pag. X).

Contexto:
{contexto}

Pregunta: {pregunta}"""


def responder(pregunta, carrera, curso=None):
    """
    Punto de entrada. Devuelve un diccionario con:
      respuesta      -> texto para mostrar
      citas          -> lista de {fuente, pagina, path} para el visor
      con_respaldo   -> True si la respuesta se apoya en documentos
    """
    # capa social: saludos, gracias, "ayuda" -> respondemos sin buscar
    social = _mensaje_social(pregunta)
    if social is not None:
        return {"respuesta": social, "citas": [], "con_respaldo": True}

    scopes = scopes_de(carrera, curso)
    filtro = {"scope": {"$in": scopes}}

    # 1. RECUPERAR fragmentos relevantes
    hits = vectorstore.buscar(pregunta, k=TOP_K, filtro=filtro)
    if not hits:
        return {"respuesta": "Aun no hay documentos para responder esto.",
                "citas": [], "con_respaldo": False}

    # 2. UMBRAL (capa anti-alucinacion 1): si nada se parece lo suficiente,
    #    no llamamos al LLM. Evita que responda desde su memoria general.
    if min(h["distancia"] for h in hits) > UMBRAL:
        return {"respuesta": ABSTENCION, "citas": [], "con_respaldo": False}

    # 3. Preparar CITAS (fuentes distintas, hasta MAX_CITAS)
    usados = [h for h in hits if h["distancia"] <= UMBRAL]
    vistos, citas = set(), []
    for h in usados:
        clave = (h["meta"]["fuente"], h["meta"]["pagina"])
        if clave not in vistos:
            vistos.add(clave)
            citas.append({
                "fuente": h["meta"]["fuente"],
                "pagina": h["meta"]["pagina"],
                "path": h["meta"].get("path", ""),
            })
        if len(citas) >= MAX_CITAS:
            break

    # 4. GENERAR con el LLM
    texto = llm.generar(_prompt(pregunta, usados))

    # 5. Si el LLM fallo o no hay key -> modo degradado: mostrar el contexto crudo
    if not texto:
        crudo = "\n\n".join(f"- {h['texto']} ({h['meta']['fuente']}, pag. {h['meta']['pagina']})"
                            for h in usados[:2])
        return {"respuesta": "(Segun los documentos oficiales:)\n\n" + crudo,
                "citas": citas, "con_respaldo": True}

    # 6. Si el modelo se abstuvo, no mostramos citas (coherencia)
    if ABSTENCION[:30].lower() in texto.lower():
        return {"respuesta": ABSTENCION, "citas": [], "con_respaldo": False}

    return {"respuesta": texto, "citas": citas, "con_respaldo": True}
