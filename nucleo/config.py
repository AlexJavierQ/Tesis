# -*- coding: utf-8 -*-
"""
Carga de configuracion secreta (API key del modelo de lenguaje).

Prioridad: variables de entorno > archivo secretos.toml (raiz del proyecto).
Asi el servidor de produccion puede inyectar la key sin editar archivos.
Por compatibilidad tambien se lee la ubicacion antigua .streamlit/secrets.toml.
El archivo de secretos NUNCA se sube al repositorio (esta en .gitignore).
"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = [
    os.path.join(BASE, "secretos.toml"),
    os.path.join(BASE, ".streamlit", "secrets.toml"),   # ubicacion antigua
]


def cargar():
    """Lee el primer archivo de secretos que exista y vuelca sus valores al entorno."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        return
    for ruta in ARCHIVOS:
        if os.path.exists(ruta):
            with open(ruta, "rb") as f:
                datos = tomllib.load(f)
            for clave in ("GROQ_API_KEY", "ADMIN_PASSWORD"):
                if clave in datos and str(datos[clave]).strip():
                    os.environ.setdefault(clave, str(datos[clave]))
            return


def hay_key():
    """True si esta configurada la key del proveedor. False = modo degradado."""
    valor = os.environ.get("GROQ_API_KEY", "")
    return bool(valor) and "TU_KEY_AQUI" not in valor


# se ejecuta al importar este modulo
cargar()
