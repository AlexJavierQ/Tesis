# -*- coding: utf-8 -*-
"""
PRUEBAS DE INTEGRIDAD: permisos, versionado, trazabilidad y recuperacion ante fallos.

Uso:  python -m pruebas.integridad

Trabaja con un curso y usuarios TEMPORALES que se crean al empezar y se borran
al terminar; los documentos oficiales no se tocan. Al final la base vectorial
debe quedar exactamente como estaba.

Que comprueba:
  1. Un PDF sin texto se rechaza sin dejar archivos ni registros.
  2. Subir con el mismo nombre crea versiones; ChromaDB solo tiene la vigente.
  3. Restaurar crea una version nueva (estilo git revert).
  4. Desactivar quita los vectores; activar los devuelve.
  5. Si la BD falla a mitad de una subida, archivos y catalogo vuelven a como estaban.
  6. Permisos: quien puede listar documentos y ver paginas de PDF.
  7. Las citas del chat guardan documento, version y seccion.
"""
import glob
import hashlib
import os
import secrets
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from interfaces.api import app  # noqa: E402
from nucleo import auth, bd, ingest, rag, vectorstore  # noqa: E402

CARRERA = bd.CARRERA_POR_DEFECTO
CURSO = "zz prueba de integridad"
CARPETA = os.path.join(rag.DOCS, CARRERA, "cursos", CURSO)
PDF_A = os.path.join(rag.DOCS, CARRERA, "cursos", "Practicum 2", "Practicum2_Entorno_Laboral_2024.pdf")
PDF_B = os.path.join(rag.DOCS, CARRERA, "global", "Modelo_de_Practicas_Preprofesionales_RR_2023.pdf")

cl = TestClient(app)
fallos = []
sufijo = secrets.token_hex(3)
clave = secrets.token_urlsafe(12)
USUARIOS = {rol: f"prueba_{rol}_{sufijo}" for rol in ("coordinacion", "docente", "estudiante", "administrador")}


def chk(nombre, condicion, detalle=""):
    print(("  OK    " if condicion else "  FALLO ") + nombre + (f"  ({detalle})" if detalle and not condicion else ""))
    if not condicion:
        fallos.append(nombre)


def sesion(rol):
    r = cl.post("/login", json={"usuario": USUARIOS[rol], "password": clave})
    return {"Authorization": "Bearer " + r.json()["token"]}


def vectores_de(doc_id):
    return [m for m in vectorstore.metadatos().values() if m.get("documento_id") == doc_id]


def subir(cabecera, nombre, contenido):
    return cl.post("/documentos", data={"carrera": CARRERA, "curso": CURSO},
                   files={"archivo": (nombre, contenido, "application/pdf")}, headers=cabecera)


def main():
    fragmentos_antes = vectorstore.contar()
    for rol, u in USUARIOS.items():
        auth.crear_usuario(u, f"Prueba {rol}", f"{u}@prueba.local", clave, rol,
                           [] if rol == "administrador" else [CARRERA])
    bd.crear_curso(CARRERA, CURSO)
    bd.asignar_docentes(CARRERA, CURSO, [USUARIOS["docente"]])
    try:
        do, es, ad = sesion("docente"), sesion("estudiante"), sesion("administrador")
        a, b = open(PDF_A, "rb").read(), open(PDF_B, "rb").read()

        print("\n1. PDF sin texto")
        vacio = fitz.open()
        vacio.new_page()
        r = subir(do, "escaneado.pdf", vacio.tobytes())
        chk("se rechaza con un mensaje claro", r.status_code == 400, r.text)
        chk("no deja archivos ni registros", not glob.glob(CARPETA + "/*") and not bd.documentos_de(CARRERA, CURSO))

        print("\n2. Versionado")
        r1, r2 = subir(do, "guia.pdf", a).json(), subir(do, "guia.pdf", b).json()
        chk("se crean la version 1 y la 2", r1.get("version") == 1 and r2.get("version") == 2, (r1, r2))
        d = bd.documento(CARRERA, CURSO, "guia.pdf")
        chk("ChromaDB solo tiene la version vigente", vectores_de(d["id"]) and
            all(m["version"] == 2 for m in vectores_de(d["id"])))

        print("\n3. Restaurar")
        r3 = cl.post(f"/documentos/{d['id']}/versiones/1/restaurar", headers=do).json()
        chk("crea la version 3 con el contenido de la 1",
            r3.get("version") == 3 and r3.get("fragmentos") == r1.get("fragmentos"), r3)
        chk("la version 3 indica de cual se restauro", bd.versiones_de(d["id"])[0]["restaurada_de"] == 1)

        print("\n4. Activar / desactivar")
        cl.patch(f"/documentos/{d['id']}/estado", json={"activo": False}, headers=do)
        chk("desactivado: sin vectores", not vectores_de(d["id"]))
        cl.patch(f"/documentos/{d['id']}/estado", json={"activo": True}, headers=do)
        chk("activado: vuelven sus vectores", bool(vectores_de(d["id"])))

        print("\n5. Fallo a mitad de una subida")
        huella = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
        antes = (huella(os.path.join(CARPETA, "guia.pdf")), bd.documento(CARRERA, CURSO, "guia.pdf"))
        original = bd.registrar_version
        bd.registrar_version = lambda *x, **y: (_ for _ in ()).throw(RuntimeError("fallo simulado"))
        try:
            ingest.guardar_documento(CARRERA, CURSO, "guia.pdf", b)
            chk("el error se informa", False)
        except RuntimeError:
            chk("el error se informa", True)
        finally:
            bd.registrar_version = original
        despues = (huella(os.path.join(CARPETA, "guia.pdf")), bd.documento(CARRERA, CURSO, "guia.pdf"))
        chk("el archivo vigente no cambio", despues[0] == antes[0])
        chk("el catalogo no cambio", despues[1]["version"] == antes[1]["version"]
            and despues[1]["ruta"] == antes[1]["ruta"])
        chk("no quedan archivos temporales", not glob.glob(os.path.join(CARPETA, "_subida_*")))
        chk("catalogo e indice coherentes", ingest.reconciliar()["reindexados"] == [])

        print("\n6. Permisos")
        ref = bd.documentos_de(CARRERA)[0]["ruta"]
        chk("estudiante no lista documentos",
            cl.get("/documentos", params={"carrera": CARRERA}, headers=es).status_code == 403)
        chk("docente no lista la normativa general",
            cl.get("/documentos", params={"carrera": CARRERA}, headers=do).status_code == 403)
        chk("estudiante de la carrera ve la pagina citada",
            cl.get("/documentos/pagina", params={"ref": ref, "pagina": 1}, headers=es).status_code == 200)
        chk("administrador sin carreras no ve archivos",
            cl.get("/documentos/info", params={"ref": ref}, headers=ad).status_code == 403)
        chk("una ruta manipulada se rechaza",
            cl.get("/documentos/info", params={"ref": "../../secretos.toml"}, headers=es).status_code in (400, 404))

        print("\n7. Trazabilidad de las citas")
        r = cl.post("/preguntar", json={"pregunta": "¿El prácticum tiene evaluación de recuperación?",
                                        "carrera": CARRERA}, headers=es).json()
        if r.get("degradado"):
            print("  AVISO el modelo no respondio (limite de Groq); se revisan igual las citas")
        chk("cada cita guarda documento, version y seccion",
            r["citas"] and all(c.get("documento_id") and c.get("version") and "seccion" in c for c in r["citas"]))
    finally:
        d = bd.documento(CARRERA, CURSO, "guia.pdf")
        if d:
            ingest.borrar_documento(d["id"])
        with bd.transaccion() as c:
            c.execute("DELETE FROM cursos WHERE nombre=?", (CURSO,))
            c.execute("DELETE FROM consultas WHERE usuario_id IS NULL AND pregunta LIKE '%evaluación de recuperación%'")
        for u in USUARIOS.values():
            uid = bd.id_usuario(u)
            if uid:
                with bd.transaccion() as c:
                    c.execute("DELETE FROM consultas WHERE usuario_id=?", (uid,))
                    c.execute("DELETE FROM logs WHERE usuario_id=?", (uid,))
            auth.borrar_usuario(u)
        shutil.rmtree(CARPETA, ignore_errors=True)

    print("\n8. Limpieza")
    chk("la base vectorial quedo como estaba", vectorstore.contar() == fragmentos_antes,
        f"{fragmentos_antes} -> {vectorstore.contar()}")
    print("\nRESULTADO:", "todo correcto" if not fallos else f"{len(fallos)} fallos: {fallos}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
