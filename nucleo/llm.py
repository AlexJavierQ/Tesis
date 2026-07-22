# -*- coding: utf-8 -*-
"""
ADAPTADOR del modelo de lenguaje (LLM). Aísla el proveedor.
Cambiar de IA = una variable de entorno LLM_PROVIDER, sin tocar nada más.

  LLM_PROVIDER=groq     (por defecto)  -> usa GROQ_API_KEY     (Llama 3.1 8B = 14.400 req/dia)
  LLM_PROVIDER=gemini                  -> usa GEMINI_API_KEY   (~1000-1500 req/dia con key real)

El defecto es groq porque es el proveedor documentado en el TIC y el que tiene
cuota gratuita suficiente para el piloto.

NUNCA lanza: devuelve None si no hay key / se agota la cuota / falla,
y el orquestador (rag.py) hace fallback a mostrar los documentos.
"""
import os
import time
from nucleo import config  # carga secrets.toml al entorno antes de leer PROVIDER

PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()
GEMINI_MODEL = "gemini-2.5-flash-lite"
GROQ_MODEL = "llama-3.1-8b-instant"          # 14.400 req/dia gratis; subir a llama-3.3-70b-versatile si se quiere mas calidad
MODEL = GROQ_MODEL if PROVIDER == "groq" else GEMINI_MODEL   # para /salud


TEMPERATURA = 0.2          # generacion: algo de flexibilidad al redactar
TEMPERATURA_JUICIO = 0.0   # verificacion: es una decision binaria, sin creatividad


def generate(prompt, api_key=None, temperatura=TEMPERATURA):
    if PROVIDER == "groq":
        return _groq(prompt, temperatura)
    return _gemini(prompt, api_key, temperatura)


def _gemini(prompt, api_key=None, temperatura=TEMPERATURA):
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={"temperature": temperatura},
        )
        for intento in range(2):
            try:
                r = model.generate_content(prompt)
                t = (r.text or "").strip()
                if t:
                    return t
            except Exception:
                if intento == 0:
                    time.sleep(3)
                else:
                    return None
    except Exception:
        return None
    return None


def _groq(prompt, temperatura=TEMPERATURA):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    import requests
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": GROQ_MODEL, "temperature": temperatura,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return None
    except Exception:
        return None
