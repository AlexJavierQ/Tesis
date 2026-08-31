# -*- coding: utf-8 -*-
"""
UN SOLO COMANDO para arrancar todo el sistema.

    python arrancar.py

Hace todo lo necesario:
  1. Indexa los PDF si el indice esta vacio.
  2. Crea los usuarios demo si no existen.
  3. Arranca la API FastAPI en http://localhost:8000
  4. Arranca el frontend React en http://localhost:5173

Requisito previo: ya debe haber PDFs en datos/docs/<carrera>/global/ (y
opcionalmente en datos/docs/<carrera>/cursos/<curso>/). El coordinador
o docente pueden subirlos despues desde la interfaz.

Usuarios demo:
  estudiante / demo2026
  docente    / demo2026
  coord      / demo2026

Ctrl+C para parar TODO.
"""
import os
import sys
import subprocess
import atexit
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)


def paso(texto):
    print(f"\n>>> {texto}")


def preparar():
    """Indexa si el vectorstore esta vacio y siembra usuarios (auth lo hace al importar)."""
    from nucleo import vectorstore, ingest, auth  # noqa: F401  (auth crea usuarios demo)

    if vectorstore.contar() == 0:
        paso("Indice vacio. Indexando el corpus de datos/docs/...")
        ingest.indexar_todo()
    else:
        paso(f"Indice OK ({vectorstore.contar()} fragmentos).")

    paso("Usuarios demo listos: estudiante / docente / coord (pass: demo2026)")


def instalar_react():
    """Corre npm install si no existe node_modules."""
    react = os.path.join(BASE, "interfaces", "react")
    if not os.path.isdir(os.path.join(react, "node_modules")):
        paso("Instalando dependencias de React (npm install)...")
        subprocess.check_call(["npm", "install"], cwd=react, shell=True)


def main():
    preparar()
    instalar_react()

    paso("Arrancando la API en http://localhost:8000  (docs en /docs)")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "interfaces.api:app",
         "--host", "127.0.0.1", "--port", "8000",
         "--reload", "--log-level", "warning"],
        cwd=BASE,
    )
    atexit.register(api.terminate)

    time.sleep(3)

    paso("Arrancando React en http://localhost:5173")
    react = os.path.join(BASE, "interfaces", "react")
    try:
        subprocess.call(["npm", "run", "dev"], cwd=react, shell=True)
    finally:
        api.terminate()


if __name__ == "__main__":
    main()
