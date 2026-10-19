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
import re
from nucleo import vectorstore, llm, bd

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


# ---------- estructura (la define la BD, no las carpetas) ----------
def carreras():
    """Lista las carreras registradas en la BD."""
    return bd.carreras()


def cursos(carrera):
    """Lista los cursos de una carrera registrados en la BD."""
    return bd.cursos(carrera)


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


# ---------- memoria conversacional ----------
def _es_seguimiento(pregunta):
    """
    ¿La pregunta depende del turno anterior? ("y cuantas son", "como las
    distribuyo"). Si es corta o empieza con un conector / pronombre, hay que
    resolverla con el historial antes de buscar.
    """
    q = pregunta.lower().strip(" ?!.,")
    if len(q.split()) <= 3:
        return True
    pistas = (r"^(y|pero|entonces|ademas|osea|o sea)\b",
              r"\b(eso|esa|ese|esto|esas|esos|aquello|lo mismo|ahi)\b",
              r"^(y\s+)?como\b", r"otra vez", r"mas (simple|detalle|claro|facil)")
    return any(re.search(p, q) for p in pistas)


def _ultima_pregunta_usuario(historial):
    """Texto del ultimo mensaje con rol 'user' en el historial, o None."""
    for m in reversed(historial or []):
        if m.get("rol") in ("user", "usuario"):
            return (m.get("texto") or "").strip()
    return None


def _contextualizar(pregunta, historial):
    """
    Ancla un seguimiento con la ULTIMA pregunta del usuario para que la
    recuperacion tenga tema: "y como las distribuyo" se busca junto a
    "cuantas horas necesito". Es concatenacion (deterministica, sin llamar
    al LLM, sin deriva).
    """
    ultima = _ultima_pregunta_usuario(historial)
    return f"{ultima} {pregunta}" if ultima else pregunta


# ---------- helpers del flujo ----------
def _contexto(hits):
    """Texto de los fragmentos, cada uno etiquetado con su fuente y pagina."""
    return "\n\n".join(
        f"[Fuente: {h['meta']['fuente']}, pag. {h['meta']['pagina']}]\n{h['texto']}"
        for h in hits
    )


def _bajo_umbral(hits):
    """Deja solo los fragmentos lo bastante parecidos (capa anti-alucinacion 1)."""
    return [h for h in hits if h["distancia"] <= UMBRAL]


def _citas_de(usados):
    """Hasta MAX_CITAS fuentes distintas (sin repetir archivo+pagina)."""
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
    return citas


def _empaquetar(texto, usados):
    """
    Arma la respuesta final a partir del texto del LLM y los fragmentos usados.
    Cubre los 3 casos: LLM caido (modo degradado), abstencion, y respuesta ok.
    """
    citas = _citas_de(usados)
    if not texto:  # LLM fallo o sin key -> mostrar el contexto crudo
        crudo = "\n\n".join(f"- {h['texto']} ({h['meta']['fuente']}, pag. {h['meta']['pagina']})"
                            for h in usados[:2])
        return {"respuesta": "(Segun los documentos oficiales:)\n\n" + crudo,
                "citas": citas, "con_respaldo": True}
    if ABSTENCION[:30].lower() in texto.lower():  # el modelo se abstuvo
        return {"respuesta": ABSTENCION, "citas": [], "con_respaldo": False}
    return {"respuesta": texto, "citas": citas, "con_respaldo": True}


# ---------- prompts ----------
def _prompt(pregunta, hits):
    """Prompt normal: un solo bloque de contexto."""
    return f"""Eres el asistente de Practicum de la UTPL. Responde SOLO usando
el contexto que sigue. Si el dato exacto no esta en el contexto, contesta
EXACTAMENTE esto y nada mas:
{ABSTENCION}

Si tienes la respuesta, redactala breve y clara en espanol, y al final agrega
(Fuente: archivo, pag. X).

Contexto:
{_contexto(hits)}

Pregunta: {pregunta}"""


def _prompt_doble(pregunta, generales, del_curso, curso):
    """
    Prompt cuando hay contexto GENERAL (reglamentos de la carrera) Y ESPECIFICO
    (material del curso). Le pide al modelo distinguir ambos en la respuesta.
    """
    return f"""Eres el asistente de Practicum de la UTPL. El estudiante pregunta
desde el curso "{curso}". Tienes DOS fuentes de contexto.

CONTEXTO GENERAL (reglamentos de la carrera):
{_contexto(generales)}

CONTEXTO ESPECIFICO DEL CURSO "{curso}":
{_contexto(del_curso)}

Responde SOLO con la informacion de los contextos. Si AMBOS aportan algo
relevante, estructura la respuesta en dos lineas asi:
  En general: <lo que dicen los reglamentos de la carrera>
  En {curso}: <lo que dice el material del curso>
Si solo uno de los dos aplica, responde directo sin esa estructura. Si el dato
no esta en ningun contexto, responde EXACTAMENTE esto y nada mas:
{ABSTENCION}

Al final agrega (Fuente: archivo, pag. X).

Pregunta: {pregunta}"""


MODOS = ("general", "curso", "ambos")


def _buscar(q, carrera, curso=None):
    """Busca en UN ambito (global de la carrera, o un curso) y aplica el umbral."""
    scope = f"{carrera}|curso:{curso}" if curso else f"{carrera}|global"
    return _bajo_umbral(vectorstore.buscar(q, k=TOP_K, filtro={"scope": scope}))


def modo_efectivo(curso, modo):
    """
    El estudiante elige en el chat desde donde quiere la respuesta:
      general -> solo los reglamentos generales de la carrera
      curso   -> solo el material del curso elegido
      ambos   -> los dos, distinguiendo "En general" / "En <curso>"
    Si no elige (p. ej. el widget publico): con curso = ambos, sin curso = general.
    Sin curso no se puede responder "desde un curso": se cae a general.
    """
    if modo not in MODOS:
        modo = "ambos" if curso else "general"
    if not curso:
        modo = "general"
    return modo


def responder(pregunta, carrera, curso=None, historial=None, modo=None):
    """
    Punto de entrada. Devuelve {respuesta, citas, con_respaldo, modo}.

    modo: "general" | "curso" | "ambos" (ver modo_efectivo).

    historial: mensajes previos de la conversacion [{rol, texto}]. Si la
    pregunta es un seguimiento ("y como las distribuyo"), se ancla con la
    pregunta anterior para que la busqueda tenga tema.
    """
    modo = modo_efectivo(curso, modo)

    # capa social: saludos, gracias, "ayuda" -> respondemos sin buscar
    social = _mensaje_social(pregunta)
    if social is not None:
        return {"respuesta": social, "citas": [], "con_respaldo": True, "modo": modo}

    # memoria conversacional: si es seguimiento, ancla la busqueda y la pregunta
    q = pregunta
    if historial and _es_seguimiento(pregunta):
        q = _contextualizar(pregunta, historial)

    generales = _buscar(q, carrera) if modo in ("general", "ambos") else []
    del_curso = _buscar(q, carrera, curso) if modo in ("curso", "ambos") else []

    if not generales and not del_curso:              # nada relevante -> abstencion
        r = {"respuesta": ABSTENCION, "citas": [], "con_respaldo": False}
    elif generales and del_curso:                    # ambos aportan -> distinguir
        texto = llm.generar(_prompt_doble(q, generales, del_curso, curso))
        # citas: dos del curso (mas especificas) y luego las generales, para
        # que el estudiante vea respaldo de AMBAS fuentes
        r = _empaquetar(texto, del_curso[:2] + generales + del_curso[2:])
    else:                                            # solo uno aporta -> normal
        usados = del_curso or generales
        r = _empaquetar(llm.generar(_prompt(q, usados)), usados)
    r["modo"] = modo
    return r
