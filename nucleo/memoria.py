# -*- coding: utf-8 -*-
"""
MEMORIA CONVERSACIONAL.

Problema: en un chat, muchas preguntas dependen de lo anterior ("¿y cuantas
son del Practicum 2?", "¿quien me lo evalua?"). Buscadas solas en los
documentos no tienen tema y la recuperacion falla.

Hay dos estrategias (el administrador elige con el parametro memoria_modo):

1) "concatenacion" (la original, sin costo extra)
   Si la pregunta parece un seguimiento (regla simple en rag._es_seguimiento),
   se le pega delante la pregunta anterior del estudiante. Solo mira 1 turno
   atras y depende de la regla.

2) "resumen" (la actual)
   Se arma un CONTEXTO de la conversacion con dos partes:
     - ventana: los ultimos `memoria_ventana` mensajes, completos;
     - resumen: lo anterior a la ventana, condensado por el modelo. Se guarda
       en conversaciones.resumen y solo se recalcula cuando un mensaje sale
       de la ventana (no en cada pregunta).
   Con ese contexto, el modelo REESCRIBE la pregunta para que se entienda
   sola. Esa pregunta reescrita es la que se busca en los documentos.

IMPORTANTE (anti-alucinacion): la memoria sirve para ENTENDER la pregunta,
nunca como fuente de la respuesta. El prompt de respuesta sigue recibiendo
solo los fragmentos de los documentos; el resumen no guarda cifras ni reglas,
solo los temas tratados y lo que el estudiante dijo de si mismo.
"""
from nucleo import historial, llm, parametros

MAX_CHARS_MENSAJE = 400   # recorta respuestas largas del bot al armar el contexto


def modo():
    return parametros.obtener("memoria_modo")


def _transcribir(mensajes):
    """Convierte mensajes en texto 'Estudiante: ... / Asistente: ...'."""
    lineas = []
    for m in mensajes:
        quien = "Estudiante" if m["rol"] == "user" else "Asistente"
        texto = " ".join(m["texto"].split())
        if len(texto) > MAX_CHARS_MENSAJE:
            texto = texto[:MAX_CHARS_MENSAJE] + "..."
        lineas.append(f"{quien}: {texto}")
    return "\n".join(lineas)


# ---------- resumen incremental ----------
def _prompt_resumen(resumen_anterior, mensajes):
    return f"""Actualiza el resumen de una conversacion entre un estudiante y el
asistente de Practicum de la UTPL. Escribe como maximo 120 palabras, en dos partes:

Temas consultados: que pregunto el estudiante y de que trato cada respuesta. NO
copies cifras, plazos ni reglas de las respuestas (esos datos siempre se vuelven a
buscar en los documentos oficiales).
Datos del estudiante: solo lo que el ESTUDIANTE dijo de si mismo (su curso, horas
que ya hizo, empresa, fechas). Si no dijo nada, escribe "ninguno".

Resumen anterior:
{resumen_anterior or "(vacio)"}

Mensajes nuevos que debes incorporar:
{_transcribir(mensajes)}

Resumen actualizado:"""


def _actualizar_resumen(conversacion_id, viejos):
    """
    Incorpora al resumen los mensajes que salieron de la ventana y aun no
    estaban resumidos. Si el modelo falla, se deja el resumen anterior.
    """
    resumen, hasta = historial.resumen_de(conversacion_id)
    pendientes = [m for m in viejos if m["id"] > hasta]
    if not pendientes:
        return resumen
    nuevo = llm.generar(_prompt_resumen(resumen, pendientes),
                        proposito="resumen", esfuerzo="low")
    if not nuevo:
        return resumen
    historial.guardar_resumen(conversacion_id, nuevo, pendientes[-1]["id"])
    return nuevo


def preparar(conversacion_id):
    """
    Contexto de memoria de una conversacion: {"resumen", "recientes"}.
    En modo concatenacion no llama al modelo: devuelve los mensajes tal cual.
    """
    mensajes = historial.mensajes_de(conversacion_id)
    if modo() != "resumen":
        return {"resumen": "", "recientes": mensajes}
    ventana = parametros.obtener("memoria_ventana")
    recientes, viejos = mensajes[-ventana:], mensajes[:-ventana]
    resumen = _actualizar_resumen(conversacion_id, viejos) if viejos else ""
    return {"resumen": resumen or "", "recientes": recientes}


# ---------- reescritura de la pregunta ----------
def _prompt_reescritura(pregunta, memoria):
    return f"""Reescribe el ULTIMO mensaje del estudiante para que se entienda
solo, sin necesidad de leer la conversacion.

Reglas:
- Si empieza con "y", "pero", "entonces", o le falta el sujeto ("cuantas
  corresponden...", "en que se diferencia..."), completalo con el tema de la
  conversacion. Esas preguntas NUNCA se entienden solas.
- Reemplaza referencias como "eso", "esa figura", "lo", "el otro" por lo que
  significan segun la conversacion.
- Cambia lo minimo: no agregues detalles, condiciones ni datos que el estudiante
  no pidio en ese mensaje.
- Si el mensaje no es una pregunta (es un comentario o un dato), devuelvelo igual.
- Si ya se entiende solo, devuelvelo igual.
- No lo respondas. Devuelve SOLO el mensaje reescrito, en una sola linea.

Ejemplos (de otra conversacion):
  Tema: requisitos de la matricula. Mensaje: "¿Y cuanto cuesta?"
  -> "¿Cuanto cuesta la matricula?"
  Tema: el tutor de tesis. Mensaje: "¿Y cada cuanto me reuno con el?"
  -> "¿Cada cuanto me reuno con el tutor de tesis?"
  Tema: becas. Mensaje: "Gracias, ya entendi."
  -> "Gracias, ya entendi."

Resumen de la conversacion anterior:
{memoria.get("resumen") or "(no hay)"}

Mensajes recientes:
{_transcribir(memoria.get("recientes", [])) or "(no hay)"}

Ultima pregunta del estudiante: {pregunta}
Pregunta reescrita:"""


def reescribir(pregunta, memoria):
    """Pregunta autonoma segun la memoria, o None si el modelo falla."""
    texto = llm.generar(_prompt_reescritura(pregunta, memoria),
                        proposito="reescritura", esfuerzo="low")
    if not texto:
        return None
    linea = texto.strip().splitlines()[0].strip().strip('"').strip()
    # una "pregunta" muy larga indica que el modelo se salio de la tarea
    # (p. ej. empezo a responder): se descarta y se usa el plan B
    if not linea or len(linea) > 300:
        return None
    return linea
