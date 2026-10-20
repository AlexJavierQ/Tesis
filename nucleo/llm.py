# -*- coding: utf-8 -*-
"""
ADAPTADOR del modelo de lenguaje.

Se usa Groq (gpt-oss-20b) porque:
  - es gratis con cuota generosa (miles de peticiones al dia)
  - buena calidad para tareas RAG (responder a partir de un contexto dado)
  - no requiere tarjeta de credito

Si el LLM falla o no hay key, devuelve None y quien lo llamo decide que hacer
(rag.py degrada la respuesta a mostrar los fragmentos crudos; la memoria
vuelve a la concatenacion simple).

MEDICION: dentro de un bloque `with llm.medir() as registro:` cada llamada
anota en `registro` su proposito, tokens de entrada/salida y segundos. Se usa
para comparar el costo de las distintas estrategias de memoria.
"""
import os
import time
import threading
from contextlib import contextmanager

import requests
from nucleo import config  # noqa: F401  -> carga la key al importar este modulo
from nucleo import parametros

URL = "https://api.groq.com/openai/v1/chat/completions"
# el modelo y la temperatura son parametros editables por el administrador
# (si Groq retira un modelo, se cambia desde la interfaz sin tocar codigo)

REINTENTOS = 2          # si Groq responde 429 (limite de peticiones), reintenta
ESPERA_MAX = 10         # segundos maximos de espera entre reintentos

_hilo = threading.local()


@contextmanager
def medir():
    """Activa el registro de consumo de las llamadas hechas en este hilo."""
    _hilo.registro = []
    try:
        yield _hilo.registro
    finally:
        _hilo.registro = None


def _anotar(proposito, uso, segundos, ok, espera=0.0):
    """segundos = duracion de la llamada que valio; espera = tiempo perdido en reintentos."""
    registro = getattr(_hilo, "registro", None)
    if registro is not None:
        registro.append({
            "proposito": proposito,
            "tokens_entrada": (uso or {}).get("prompt_tokens", 0),
            "tokens_salida": (uso or {}).get("completion_tokens", 0),
            "segundos": round(segundos, 3),
            "espera_limite": round(espera, 3),
            "ok": ok,
        })


def generar(prompt, proposito="respuesta", esfuerzo=None):
    """
    Envia el prompt a Groq y devuelve la respuesta (o None si falla).
    proposito: etiqueta para la medicion ("respuesta", "reescritura", "resumen").
    esfuerzo: "low" | "medium" | "high" -> cuanto "razona" el modelo antes de
              responder (solo modelos gpt-oss). Las tareas auxiliares usan "low"
              para gastar menos tokens y tiempo.
    """
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    modelo = parametros.obtener("modelo_llm")
    cuerpo = {
        "model": modelo,
        "temperature": parametros.obtener("temperatura"),
        "messages": [{"role": "user", "content": prompt}],
    }
    if esfuerzo and modelo.startswith("openai/gpt-oss"):
        cuerpo["reasoning_effort"] = esfuerzo

    espera_total = 0.0
    for intento in range(REINTENTOS + 1):
        inicio = time.perf_counter()
        try:
            respuesta = requests.post(URL, headers={"Authorization": f"Bearer {key}"},
                                      json=cuerpo, timeout=30)
        except Exception:
            _anotar(proposito, None, time.perf_counter() - inicio, False, espera_total)
            return None
        if respuesta.status_code == 429 and intento < REINTENTOS:
            espera = float(respuesta.headers.get("retry-after", 2) or 2)
            # si Groq pide esperar mucho (p. ej. se agoto la cuota DIARIA de
            # tokens) no vale la pena: se falla ya y se usa el plan B
            if espera > ESPERA_MAX:
                break
            espera_total += (time.perf_counter() - inicio) + espera
            time.sleep(espera)
            continue
        break

    segundos = time.perf_counter() - inicio
    if respuesta.status_code != 200:
        _anotar(proposito, None, segundos, False, espera_total)
        return None
    datos = respuesta.json()
    msg = datos["choices"][0]["message"]
    # Algunos modelos "razonan" y devuelven el pensamiento en `reasoning`
    # y la respuesta final en `content`. Priorizamos `content`, y si viene
    # vacio usamos `reasoning`.
    texto = (msg.get("content") or msg.get("reasoning") or "").strip()
    _anotar(proposito, datos.get("usage"), segundos, bool(texto), espera_total)
    return texto or None
