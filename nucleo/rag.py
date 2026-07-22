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
import re
import unicodedata
from difflib import SequenceMatcher

from nucleo import vectorstore
from nucleo import llm

BASE = os.path.dirname(__file__)
DOCS = os.path.join(os.path.dirname(BASE), "datos", "docs")

# --- parametros del motor (documentados en el Cap. 3 del TIC) ---
TOP_K = 8          # fragmentos recuperados por consulta (barrido: recall@8 = 93 %
                   # frente a 84 % con k=5; a partir de 12 la mejora no compensa
                   # el contexto extra que se manda al modelo)
THRESHOLD = 0.65   # distancia coseno maxima admitida (0 = identico, 2 = opuesto)
MAX_CITAS = 3      # fuentes distintas que se muestran al usuario

# Capa 3 opcional: segunda llamada al modelo para verificar el respaldo.
# APAGADA POR DEFECTO. Se midio y su aporte es CERO: rechaza 0 de las respuestas
# infundadas, porque el verificador es el mismo modelo y comparte el punto ciego
# del generador (confunde "el contexto trata el tema" con "el contexto responde").
# Cuesta una llamada extra por consulta. Se enciende con VERIFICAR_RESPUESTA=1.
# Detalle del experimento en documentacion/ANTIALUCINACION.md
VERIFICAR = os.environ.get("VERIFICAR_RESPUESTA", "0") == "1"

# Capa 3: cita literal verificada mecanicamente. ENCENDIDA por defecto.
# El generador copia la frase textual del contexto que respalda su respuesta y se
# comprueba por comparacion de cadenas que esa frase existe. Es DETERMINISTA (no
# vuelve a preguntar al modelo) y no anade latencia.
# Medido: NO mejora la abstencion (los fallos son de razonamiento, no de
# fabricacion), pero GARANTIZA que ninguna respuesta se apoye en texto inexistente
# -> unica defensa estructural contra la fabricacion pura. Se apaga con CITA_LITERAL=0.
# Detalle en documentacion/ANTIALUCINACION.md
CITA_LITERAL = os.environ.get("CITA_LITERAL", "1") == "1"
UMBRAL_CITA = 0.72   # solape minimo frase-contexto para darla por textual

# Frase canonica de abstencion. El prompt pide EXACTAMENTE esta, y la usamos
# tanto para responder sin respaldo como para detectar que el modelo se abstuvo.
ABSTENCION = ("No tengo informacion oficial sobre eso. "
              "Te recomiendo consultar con la coordinacion.")

# Cuantos turnos previos se usan para resolver un seguimiento.
HISTORIAL_MAX = 4

AYUDA = ("Soy el asistente de Practicum. Respondo con los documentos oficiales de "
         "la UTPL. Preguntame, por ejemplo, cuantas horas necesitas, el plazo del "
         "informe, que formato usar o la nota minima. Si algo no esta en los "
         "documentos, te derivo a la coordinacion.")


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


def _normalizar(texto):
    """minusculas y sin tildes, para comparar sin depender de como se acentue."""
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def _se_abstuvo(texto):
    """
    Capa 3: detecta que el modelo NO encontro la respuesta en el contexto.
    Antes se buscaban subcadenas sueltas ('coordinaci' + 'no tengo'), que fallaba
    en cuanto el modelo redactaba distinto. Ahora se compara contra la frase
    canonica de abstencion y contra sus formulaciones equivalentes.
    """
    t = _normalizar(texto)
    if _normalizar(ABSTENCION)[:40] in t:
        return True
    niega = any(f in t for f in ("no tengo informacion", "no hay informacion",
                                 "no cuento con", "no dispongo de", "no se encuentra",
                                 "no aparece en", "no esta en el contexto",
                                 "no puedo responder"))
    deriva = "coordinacion" in t
    return niega and deriva


# ---------- capa conversacional ----------
def _social(question):
    """
    Respuesta a mensajes que NO son consultas documentales (saludos, cortesia,
    'que puedes hacer'). Antes esto solo existia en el frontend de Streamlit y la
    API los trataba como busqueda -> derivaba a coordinacion, lo que quedaba mal.
    Devuelve el texto de respuesta, o None si es una consulta normal.
    """
    q = _normalizar(question).strip(" ?!.,")
    palabras = q.split()
    corto = len(palabras) <= 4

    if corto and any(re.search(p, q) for p in
                     (r"\bgracias\b", r"muchas gracias", r"^ok\b", r"\bvale\b",
                      r"perfecto", r"entendido", r"listo", r"genial", r"buenisimo")):
        return "Con gusto. Si te queda otra duda sobre el Practicum, aqui estoy."
    if corto and any(re.search(p, q) for p in
                     (r"\bhola\b", r"buen[oa]s\b", r"\bhey\b", r"que tal", r"saludos")):
        return "Hola. Soy el asistente de Practicum. Preguntame sobre horas, plazos, formatos o notas."
    if any(re.search(p, q) for p in
           (r"\bayuda\b", r"que puedo pregunt", r"que puedes (hacer|responder)",
            r"como funciona", r"quien eres", r"para que sirves")):
        return AYUDA
    return None


def _es_reformulacion(question):
    """
    ¿El usuario pide reformular la respuesta ANTERIOR (no una nueva)?
    'explicamelo de otra forma', 'no entendi', 'mas simple'. Estos NO son una
    consulta documental nueva: hay que reescribir la respuesta previa, no volver
    a recuperar (y por tanto no aplican el umbral ni la cita literal).
    """
    q = _normalizar(question)
    return any(re.search(c, q) for c in (
        r"de otra (forma|manera)", r"no (lo )?entend", r"no me qued[oa] claro",
        r"explica(me|melo)?\b", r"mas (simple|facil|claro|sencill)",
        r"otra vez", r"\bresume\b", r"puedes repetir", r"repite", r"mas detalle"))


def _reformular(respuesta_previa, question, api_key=None):
    """Reescribe la respuesta anterior mas simple, sin agregar datos nuevos."""
    prompt = f"""El usuario pidio: "{question}".
Reescribe la siguiente respuesta de forma mas simple y clara, en espanol, con el
MISMO contenido. No agregues datos nuevos ni inventes nada. Manten la cita de la
fuente si la hay. Responde solo con la nueva version.

Respuesta a reformular:
{respuesta_previa}"""
    nueva = llm.generate(prompt, api_key=api_key)
    return (nueva or respuesta_previa).strip()


def _ultima_respuesta(historial):
    """Texto del ultimo turno del asistente, o None."""
    for m in reversed(historial or []):
        if m.get("rol") in ("bot", "assistant", "asistente"):
            return (m.get("texto") or m.get("txt") or "").strip()
    return None


def _es_seguimiento(question):
    """
    Heuristica: ¿esta pregunta depende del turno anterior? Si es corta o arranca
    con un conector, o pide reformular, hay que resolverla con el historial antes
    de recuperar. Evita gastar una llamada de reescritura en preguntas ya completas.
    """
    q = _normalizar(question).strip()
    if len(q.split()) <= 3:
        return True
    cues = (r"^(y|pero|entonces|ademas|osea|o sea)\b", r"\bde otra forma\b",
            r"no (lo )?entend", r"explica(me|melo)?\b", r"mas (simple|facil|claro)",
            r"\b(eso|esa|ese|esto|aquello|lo mismo|ahi)\b", r"otra vez", r"resume")
    return any(re.search(c, q) for c in cues)


def _formatear_historial(historial, n=HISTORIAL_MAX):
    """Ultimos turnos como texto plano. Acepta claves 'texto' o 'txt'."""
    if not historial:
        return ""
    lineas = []
    for m in historial[-n:]:
        rol = "Usuario" if m.get("rol") in ("user", "usuario") else "Asistente"
        txt = (m.get("texto") or m.get("txt") or "").strip()
        if txt:
            lineas.append(f"{rol}: {txt}")
    return "\n".join(lineas)


def _contextualizar(question, historial, api_key=None):
    """
    Ancla un seguimiento con la ULTIMA pregunta del usuario para que la
    RECUPERACION tenga tema: 'y cuantas horas son' se busca junto a 'que es el
    practicum'. Es concatenacion, no reescritura por LLM: se probó el reescritor
    y desviaba el sentido ('...horas comunes en un practicum') ademas de sumar
    latencia. Concatenar es deterministico, sin deriva y sin coste.
    """
    ultima_preg = None
    for m in reversed(historial or []):
        if m.get("rol") in ("user", "usuario"):
            ultima_preg = (m.get("texto") or m.get("txt") or "").strip()
            break
    if not ultima_preg:
        return question
    return f"{ultima_preg} {question}"


def _build_prompt(question, hits, historial=None):
    """
    Capa 2 + soporte de la capa 3. El prompt anterior decia solo "responde con el
    contexto", y el modelo interpretaba que un fragmento del MISMO TEMA bastaba.
    Ahora, ademas de exigir el dato concreto, se le obliga a copiar la frase
    textual que respalda la respuesta (FUNDAMENTO). Esa frase se verifica luego
    por comparacion de cadenas: si el modelo no puede copiar una frase real que
    lo sostenga, es que no estaba en el contexto.

    Si hay historial, se incluye para que el modelo resuelva el hilo (por ejemplo
    reformular la respuesta anterior 'de otra forma') sin cambiar de tema.
    """
    bloques = [f"[Fuente: {h['fuente']}, pag. {h['pagina']}]\n{h['texto']}" for h in hits]
    hist = _formatear_historial(historial)
    bloque_hist = f"\nConversacion hasta ahora:\n{hist}\n" if hist else ""
    return f"""Eres el asistente de Practicum (practicas preprofesionales) de la UTPL.

REGLA PRINCIPAL: responde SOLO si el dato exacto que se pregunta aparece escrito
en el contexto. No completes con conocimiento propio ni con lo que parezca razonable.
Que un fragmento trate el mismo tema NO significa que contenga la respuesta.

Si NO tienes la respuesta, contesta EXACTAMENTE esto y nada mas:
{ABSTENCION}

Si el usuario pide reformular o aclarar la respuesta anterior, explica LO MISMO de
otra manera, mas simple, sin cambiar de tema y sin salir del contexto.

Si SI la tienes, usa exactamente este formato de dos lineas:
RESPUESTA: <respuesta en espanol, clara y breve, con (Fuente: archivo, pag. X) al final>
FUNDAMENTO: <copia aqui, palabra por palabra, la frase del contexto que respalda tu respuesta>
{bloque_hist}
Contexto:
{chr(10).join(bloques)}

Pregunta: {question}"""


def _partir_respuesta(texto):
    """Separa la respuesta visible del FUNDAMENTO (frase de respaldo)."""
    fundamento = ""
    m = re.search(r"FUNDAMENTO\s*:\s*(.+)", texto, re.IGNORECASE | re.DOTALL)
    if m:
        fundamento = m.group(1).strip().strip('"').strip()
        texto = texto[:m.start()]
    texto = re.sub(r"^\s*RESPUESTA\s*:\s*", "", texto.strip(), flags=re.IGNORECASE)
    return texto.strip(), fundamento


def _fundamento_en_contexto(fundamento, hits):
    """
    True si el FUNDAMENTO es realmente una frase del contexto (no inventada).

    Comparacion determinista: se busca el bloque contiguo mas largo que compartan
    la frase citada y el contexto, normalizados (sin tildes, minusculas, espacios
    colapsados). Si ese bloque cubre >= UMBRAL_CITA de la frase, la damos por
    textual. Tolera pequenas variaciones de puntuacion sin aceptar parafraseos.
    """
    # El modelo a veces pega la cita "(Fuente: archivo, pag. X)" dentro del
    # FUNDAMENTO; ese sufijo no esta en el contexto y hundia el ratio, rechazando
    # respuestas validas. Se quita antes de comparar.
    limpio = re.sub(r"\(fuente[^)]*\)", " ", fundamento, flags=re.IGNORECASE)
    fund = _normalizar(limpio).strip()
    if len(fund) < 15:                       # frase demasiado corta: no verifica nada
        return False
    contexto = _normalizar(" ".join(h["texto"] for h in hits))
    sm = SequenceMatcher(None, fund, contexto, autojunk=False)
    _, _, tam = sm.find_longest_match(0, len(fund), 0, len(contexto))
    return tam / len(fund) >= UMBRAL_CITA


def _verificar(question, respuesta, hits, api_key=None):
    """
    Capa 3 reforzada: segunda llamada al modelo, actuando como VERIFICADOR.

    Se separa de la generacion a proposito. El generador esta sesgado a ser util
    (quiere responder); el verificador recibe una tarea binaria y cerrada, sin
    presion de redactar. Se le pide el veredicto ANTES de justificarlo para que
    no se convenza a si mismo razonando.

    Devuelve True si la respuesta esta respaldada, False si no.
    Ante fallo de red o respuesta ilegible devuelve True: la capa 1 ya filtro
    por similitud y no queremos negar servicio por un fallo de infraestructura.
    """
    contexto = "\n\n".join(h["texto"] for h in hits)
    prompt = f"""Eres un verificador de citas. Tu unica tarea es decidir si una
respuesta esta respaldada por un contexto. No corrijas ni mejores la respuesta.

CONTEXTO:
{contexto}

PREGUNTA: {question}

RESPUESTA A VERIFICAR: {respuesta}

¿El contexto contiene explicitamente el dato que afirma la respuesta?
Responde NO si la respuesta se apoya en algo que el contexto no dice, aunque
trate del mismo tema. Tratar el mismo tema no es contener la respuesta.

Contesta con una sola palabra, RESPALDADA o INFUNDADA, y nada mas."""

    veredicto = llm.generate(prompt, api_key=api_key,
                             temperatura=llm.TEMPERATURA_JUICIO)
    if not veredicto:
        return True
    return "infundada" not in _normalizar(veredicto)[:40]


def answer(question, api_key=None, scopes=None, historial=None):
    # Mensaje social (saludo, gracias, "que puedes hacer"): no es una consulta
    # documental. Se responde con cortesia, sin recuperar ni derivar.
    social = _social(question)
    if social is not None:
        return {"respuesta": social, "fuentes": [], "citas": [],
                "con_respaldo": True, "social": True}

    # Reformulacion ("explicamelo de otra forma", "no entendi"): se reescribe la
    # respuesta anterior, sin recuperar de nuevo. Solo si la anterior fue una
    # respuesta real (no una abstencion ni un saludo).
    if historial and _es_reformulacion(question):
        previa = _ultima_respuesta(historial)
        if previa and not _se_abstuvo(previa) and _social(previa) is None:
            return {"respuesta": _reformular(previa, question, api_key),
                    "fuentes": [], "citas": [], "con_respaldo": True, "social": True}

    # Seguimiento ("y cuantas horas son"): pregunta nueva que depende del hilo. Se
    # reescribe como pregunta autonoma para que la recuperacion tenga tema.
    q_busqueda = question
    if historial and _es_seguimiento(question):
        q_busqueda = _contextualizar(question, historial, api_key=api_key)

    hits = retrieve(q_busqueda, scopes=scopes)
    if not hits:
        return {"respuesta": "Aun no hay documentos para responder esto.",
                "fuentes": [], "citas": [], "con_respaldo": False}
    if min(h["distancia"] for h in hits) > THRESHOLD:
        # Capa 1: ningun fragmento se parece lo suficiente -> no se llama al LLM.
        return {"respuesta": ABSTENCION, "fuentes": [], "citas": [], "con_respaldo": False}

    usados = [h for h in hits if h["distancia"] <= THRESHOLD]
    # El contexto va amplio (TOP_K) para que el modelo tenga con que responder,
    # pero se citan solo las fuentes mas cercanas: una respuesta con 5 citas no
    # ayuda a verificar, satura.
    vistos, citas = set(), []
    for h in usados:
        key = (h["fuente"], h["pagina"])
        if key not in vistos:
            vistos.add(key)
            citas.append({"fuente": h["fuente"], "pagina": h["pagina"], "path": h["path"]})
        if len(citas) >= MAX_CITAS:
            break
    fuentes_str = [f"{c['fuente']} (pag. {c['pagina']})" for c in citas]
    ctx_breve = "\n\n".join(f"- {h['texto']}  ({h['fuente']}, pag. {h['pagina']})" for h in usados[:2])

    texto = llm.generate(_build_prompt(question, usados, historial), api_key=api_key)
    if not texto:
        # sin API key o el modelo fallo -> mostramos lo recuperado (no se rompe)
        texto = "(Según los documentos oficiales:)\n\n" + ctx_breve
        return {"respuesta": texto, "fuentes": fuentes_str, "citas": citas, "con_respaldo": True}

    texto, fundamento = _partir_respuesta(texto)

    if _se_abstuvo(texto) or not texto:
        # Coherencia: si el modelo dice que no sabe, no se muestran citas.
        return {"respuesta": texto or ABSTENCION, "fuentes": [], "citas": [], "con_respaldo": False}

    # Capa 3 (determinista): la frase de respaldo tiene que existir en el contexto.
    if CITA_LITERAL and not _fundamento_en_contexto(fundamento, usados):
        return {"respuesta": ABSTENCION, "fuentes": [], "citas": [], "con_respaldo": False}

    # Capa 3 (opcional, por LLM): apagada por defecto (aporte medido = 0).
    if VERIFICAR and not _verificar(question, texto, usados, api_key=api_key):
        return {"respuesta": ABSTENCION, "fuentes": [], "citas": [], "con_respaldo": False}

    return {"respuesta": texto, "fuentes": fuentes_str, "citas": citas, "con_respaldo": True}
