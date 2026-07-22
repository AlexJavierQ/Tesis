# -*- coding: utf-8 -*-
"""
Carga de configuracion. UNICO punto donde se leen las keys.

Antes cada entrada (app.py / api.py) resolvia esto por su cuenta y api.py
directamente no lo hacia, asi que la API nunca veia la key y siempre caia
al modo degradado. Ahora ambas importan este modulo antes que el motor.

Orden de precedencia:  variables de entorno  >  .streamlit/secrets.toml
(asi el despliegue puede inyectar la key sin tocar archivos).
"""
import os

BASE = os.path.dirname(__file__)
SECRETS = os.path.join(os.path.dirname(BASE), ".streamlit", "secrets.toml")
CLAVES = ("LLM_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY")


def cargar():
    """Vuelca secrets.toml al entorno sin pisar lo que ya venga del entorno."""
    if not os.path.exists(SECRETS):
        return
    try:
        import tomllib
    except ImportError:                      # Python < 3.11
        return
    try:
        with open(SECRETS, "rb") as f:
            datos = tomllib.load(f)
    except Exception:
        return
    for k, v in datos.items():
        if k in CLAVES and str(v).strip():
            os.environ.setdefault(k, str(v))


def key_activa():
    """La key del proveedor en uso, o None si no hay ninguna configurada."""
    if os.environ.get("LLM_PROVIDER", "groq").lower() == "groq":
        valor = os.environ.get("GROQ_API_KEY")
    else:
        valor = os.environ.get("GEMINI_API_KEY")
    # el .example trae valores de relleno: no los tratamos como key valida
    if not valor or "TU_KEY_AQUI" in valor:
        return None
    return valor


cargar()
