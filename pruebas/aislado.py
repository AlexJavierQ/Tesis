# -*- coding: utf-8 -*-
"""
ENTORNO AISLADO para las pruebas unitarias.

Las pruebas que lo usan trabajan sobre una carpeta de datos TEMPORAL (base de
datos, PDF e indice vacios) y nunca tocan datos/ ni llaman al modelo de
lenguaje. La carpeta se elige con la variable PRACTICUM_DATOS, que
nucleo/config.py lee al importarse: por eso `preparar()` debe llamarse ANTES
de importar cualquier modulo de nucleo o de interfaces.

    from pruebas import aislado
    aislado.preparar()
    from interfaces.api import app   # ya apunta a la carpeta temporal
"""
import atexit
import os
import secrets
import shutil
import sys
import tempfile

_MARCA = "PRACTICUM_DATOS_ES_DE_PRUEBA"


def preparar():
    """Crea la carpeta temporal y apunta el nucleo a ella. Devuelve su ruta."""
    if os.environ.get(_MARCA):
        return os.environ["PRACTICUM_DATOS"]
    if "nucleo.config" in sys.modules:
        raise RuntimeError(
            "El nucleo ya se importo con los datos reales. Ejecuta estas pruebas "
            "en un proceso propio:  python -m unittest pruebas.test_v1_seguridad")
    carpeta = tempfile.mkdtemp(prefix="practicum_prueba_")
    os.environ["PRACTICUM_DATOS"] = carpeta
    os.environ[_MARCA] = "1"
    # contrasena del administrador inicial: aleatoria y sin mostrarla en consola
    os.environ["ADMIN_PASSWORD"] = secrets.token_urlsafe(12)
    atexit.register(shutil.rmtree, carpeta, ignore_errors=True)
    return carpeta
