# -*- coding: utf-8 -*-
"""
Carga de configuracion (API keys del LLM).

Prioridad: variables de entorno > archivo .streamlit/secrets.toml
Asi el servidor de produccion puede inyectar la key sin editar archivos.
"""
import os

BASE = os.path.dirname(__file__)
SECRETS = os.path.join(os.path.dirname(BASE), ".streamlit", "secrets.toml")


def cargar():
    """Lee secrets.toml y vuelca los valores al entorno (sin pisar los existentes)."""
    if not os.path.exists(SECRETS):
        return
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        return
    with open(SECRETS, "rb") as f:
        datos = tomllib.load(f)
    for clave in ("GROQ_API_KEY", "LLM_PROVIDER"):
        if clave in datos and str(datos[clave]).strip():
            os.environ.setdefault(clave, str(datos[clave]))


def hay_key():
    """True si esta configurada la key del proveedor. False = modo degradado."""
    valor = os.environ.get("GROQ_API_KEY", "")
    return bool(valor) and "TU_KEY_AQUI" not in valor


# se ejecuta al importar este modulo
cargar()
