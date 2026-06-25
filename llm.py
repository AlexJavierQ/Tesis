# -*- coding: utf-8 -*-
"""
ADAPTADOR del modelo de lenguaje (LLM). Aísla el proveedor.
Cambiar de IA = una variable de entorno LLM_PROVIDER, sin tocar nada más.

  LLM_PROVIDER=gemini   (por defecto)  -> usa GEMINI_API_KEY   (~1000-1500 req/dia con key real)
  LLM_PROVIDER=groq                    -> usa GROQ_API_KEY     (Llama 3.1 8B = 14.400 req/dia)

NUNCA lanza: devuelve None si no hay key / se agota la cuota / falla,
y el orquestador (rag.py) hace fallback a mostrar los documentos.
"""
import os
import time

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = "gemini-2.5-flash-lite"
GROQ_MODEL = "llama-3.1-8b-instant"          # 14.400 req/dia gratis; subir a llama-3.3-70b-versatile si se quiere mas calidad
MODEL = GROQ_MODEL if PROVIDER == "groq" else GEMINI_MODEL   # para /salud


def generate(prompt, api_key=None):
    if PROVIDER == "groq":
        return _groq(prompt)
    return _gemini(prompt, api_key)


def _gemini(prompt, api_key=None):
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(GEMINI_MODEL)
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


def _groq(prompt):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    import requests
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": GROQ_MODEL, "temperature": 0.2,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return None
    except Exception:
        return None
