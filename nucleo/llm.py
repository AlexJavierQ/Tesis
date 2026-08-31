# -*- coding: utf-8 -*-
"""
ADAPTADOR del modelo de lenguaje.

Se usa Groq (gpt-oss-20b) porque:
  - es gratis con cuota generosa (miles de peticiones al dia)
  - buena calidad para tareas RAG (responder a partir de un contexto dado)
  - no requiere tarjeta de credito

Si el LLM falla o no hay key, devuelve None y el orquestador (rag.py)
degrada la respuesta a mostrar los fragmentos crudos.
"""
import os
import requests
from nucleo import config  # noqa: F401  -> carga la key al importar este modulo

MODELO = "openai/gpt-oss-20b"
URL = "https://api.groq.com/openai/v1/chat/completions"
TEMPERATURA = 0.2  # bajo para respuestas mas fieles al contexto


def generar(prompt):
    """Envia el prompt a Groq y devuelve la respuesta (o None si falla)."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    try:
        respuesta = requests.post(
            URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": MODELO,
                "temperature": TEMPERATURA,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if respuesta.status_code == 200:
            msg = respuesta.json()["choices"][0]["message"]
            # Algunos modelos "razonan" y devuelven el pensamiento en `reasoning`
            # y la respuesta final en `content`. Otros al reves. Priorizamos
            # `content`, y si viene vacio usamos `reasoning`.
            texto = msg.get("content") or msg.get("reasoning") or ""
            return texto.strip() or None
        return None
    except Exception:
        return None
