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
from nucleo import parametros

URL = "https://api.groq.com/openai/v1/chat/completions"
# el modelo y la temperatura son parametros editables por el administrador
# (si Groq retira un modelo, se cambia desde la interfaz sin tocar codigo)


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
                "model": parametros.obtener("modelo_llm"),
                "temperature": parametros.obtener("temperatura"),
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
