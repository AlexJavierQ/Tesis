# -*- coding: utf-8 -*-
"""
UN SOLO COMANDO para arrancar todo el sistema.

    python arrancar.py

Hace todo lo necesario:
  1. Indexa los PDF si hace falta y revisa que el indice coincida con el catalogo.
  2. Crea el primer administrador si no hay usuarios.
  3. Arranca la API FastAPI en http://localhost:8000
  4. Arranca el frontend React en http://localhost:5173

Requisito previo: ya debe haber PDFs en datos/docs/<carrera>/global/ (y
opcionalmente en datos/docs/<carrera>/cursos/<curso>/). El coordinador
o docente pueden subirlos despues desde la interfaz.

Primer acceso: si la base de datos no tiene usuarios, se crea el usuario
"admin". Su contrasena es ADMIN_PASSWORD (secretos.toml o variable de entorno)
o, si no esta definida, una al azar que se muestra una vez en la consola.
Cuentas de prueba locales (opcional): python -m nucleo.auth --prueba

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
    """
    Deja los datos listos antes de arrancar:
      - crea la BD y, si no hay usuarios, el primer administrador (auth.py)
      - registra los PDF de datos/docs/ que falten en el catalogo
      - revisa que ChromaDB coincida con el catalogo y corrige diferencias
    """
    from nucleo import vectorstore, ingest, auth, bd  # noqa: F401  (auth crea el primer admin)

    with bd.transaccion() as c:
        catalogo_vacio = c.execute("SELECT COUNT(*) FROM documentos").fetchone()[0] == 0
    if vectorstore.contar() == 0 or catalogo_vacio:
        paso("Indice o catalogo vacio. Indexando el corpus de datos/docs/...")
        ingest.indexar_todo()
    else:
        informe = ingest.reconciliar()
        if informe["reindexados"] or informe["huerfanos"] or informe["limpiados"]:
            paso(f"Se corrigieron diferencias entre catalogo e indice: {informe}")
        if informe["archivos_faltantes"]:
            paso(f"ATENCION: faltan archivos de documentos: {informe['archivos_faltantes']}")
        paso(f"Indice OK ({vectorstore.contar()} fragmentos).")


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
