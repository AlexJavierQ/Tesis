# -*- coding: utf-8 -*-
"""
API REST del Asistente de Practicum (C3 - backend).
Es el UNICO backend: el frontend React la consume por HTTP.

Correr:  uvicorn interfaces.api:app --reload
Docs interactivas:  http://localhost:8000/docs
"""
import os

# permite ejecutar este archivo directamente: agrega la raiz del proyecto al path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import config                       # carga las keys ANTES de importar el motor  # noqa: F401

from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from nucleo import rag, ingest, llm, metricas, pdfreader

app = FastAPI(title="API Asistente de Practicum", version="2.0")

# En desarrollo el front corre en otro puerto (Vite: 5173), por eso hace falta CORS.
# ORIGENES se puede fijar por entorno al desplegar en vez de dejarlo abierto.
ORIGENES = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o] or [
    "http://localhost:5173", "http://127.0.0.1:5173",   # React (Vite)
    "http://localhost:5500", "http://127.0.0.1:5500",   # demo del widget embebible
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- rutas seguras ----------
def _ref(path):
    """
    Referencia relativa a docs/ que se expone al cliente.
    La ingesta ya guarda rutas relativas; se normaliza por si el indice viene
    de una version anterior que guardaba absolutas.
    """
    if not path:
        return ""
    if os.path.isabs(path):
        try:
            return os.path.relpath(path, rag.DOCS).replace("\\", "/")
        except ValueError:
            return ""
    return path.replace("\\", "/")


def _resolver(ref):
    """
    Referencia del cliente -> ruta absoluta, verificando que caiga DENTRO de docs/.
    Sin esto, un '../../..' en la referencia serviria cualquier archivo del disco.
    """
    destino = os.path.abspath(os.path.join(rag.DOCS, ref))
    raiz = os.path.abspath(rag.DOCS)
    if os.path.commonpath([destino, raiz]) != raiz:
        raise HTTPException(400, "Ruta no permitida.")
    if not os.path.exists(destino):
        raise HTTPException(404, "Documento no encontrado.")
    return destino


# ---------- modelos ----------
class Turno(BaseModel):
    rol: str            # "user" | "bot"
    texto: str


class Consulta(BaseModel):
    pregunta: str
    carrera: str
    curso: Optional[str] = None
    historial: Optional[List[Turno]] = None   # turnos previos, para seguimientos


class Cita(BaseModel):
    fuente: str
    pagina: int | str
    ref: str


class Respuesta(BaseModel):
    respuesta: str
    fuentes: List[str]
    citas: List[Cita]
    con_respaldo: bool


# ---------- estado ----------
@app.get("/salud")
def salud():
    """Estado del servicio y proveedor de LLM realmente activo."""
    return {
        "ok": True,
        "proveedor": llm.PROVIDER,
        "modelo": llm.MODEL,
        "llm_disponible": config.key_activa() is not None,
        "fragmentos_indexados": rag.vectorstore.count(),
    }


# ---------- estructura ----------
@app.get("/carreras")
def get_carreras():
    return rag.carreras()


@app.get("/carreras/{carrera}/cursos")
def get_cursos(carrera: str):
    return rag.cursos(carrera)


@app.post("/carreras/{carrera}/cursos")
def crear_curso(carrera: str, nombre: str = Form(...)):
    nombre = nombre.strip()
    if not nombre or "/" in nombre or "\\" in nombre or nombre.startswith("."):
        raise HTTPException(400, "Nombre de curso no valido.")
    os.makedirs(rag.folder_curso(carrera, nombre), exist_ok=True)
    return {"ok": True, "curso": nombre}


# ---------- consultar ----------
@app.post("/preguntar", response_model=Respuesta)
def preguntar(c: Consulta):
    """Pregunta al asistente de una carrera (y opcionalmente un curso)."""
    if not c.pregunta.strip():
        raise HTTPException(400, "La pregunta esta vacia.")
    scopes = rag.scopes_for(c.carrera, c.curso)
    historial = [t.model_dump() for t in c.historial] if c.historial else None
    r = rag.answer(c.pregunta, scopes=scopes, historial=historial)
    # los mensajes sociales (saludo, gracias) no se registran como consultas
    if not r.get("social"):
        metricas.registrar(c.pregunta, r["con_respaldo"], r["fuentes"], scopes[-1])
    return {
        "respuesta": r["respuesta"],
        "fuentes": r["fuentes"],
        "citas": [{"fuente": x["fuente"], "pagina": x["pagina"], "ref": _ref(x["path"])}
                  for x in r["citas"]],
        "con_respaldo": r["con_respaldo"],
    }


# ---------- documentos ----------
@app.get("/documentos")
def listar_documentos(carrera: str, curso: Optional[str] = None):
    scope = rag.scope_curso(carrera, curso) if curso else rag.scope_global(carrera)
    folder = rag.folder_de(scope)
    if not os.path.isdir(folder):
        return []
    salida = []
    for nombre in sorted(os.listdir(folder)):
        if nombre.lower().endswith(".pdf"):
            p = os.path.join(folder, nombre)
            salida.append({"nombre": nombre, "ref": _ref(p),
                           "paginas": pdfreader.num_paginas(p)})
    return salida


@app.post("/documentos")
def subir_documento(carrera: str = Form(...),
                    archivo: UploadFile = File(...),
                    curso: Optional[str] = Form(None)):
    """Sube un PDF como global (coordinacion) o de un curso (docente) e indexa al instante."""
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF.")
    nombre = os.path.basename(archivo.filename)       # evita rutas en el nombre
    if curso:
        folder, scope = rag.folder_curso(carrera, curso), rag.scope_curso(carrera, curso)
    else:
        folder, scope = rag.folder_global(carrera), rag.scope_global(carrera)
    os.makedirs(folder, exist_ok=True)
    destino = os.path.join(folder, nombre)
    with open(destino, "wb") as f:
        f.write(archivo.file.read())
    n = ingest.add_pdf(destino, scope)
    return {"ok": True, "archivo": nombre, "scope": scope, "fragmentos": n}


@app.delete("/documentos")
def borrar_documento(carrera: str, nombre: str, curso: Optional[str] = None):
    scope = rag.scope_curso(carrera, curso) if curso else rag.scope_global(carrera)
    nombre = os.path.basename(nombre)
    destino = os.path.join(rag.folder_de(scope), nombre)
    if not os.path.exists(destino):
        raise HTTPException(404, "Documento no encontrado.")
    ingest.remove_doc(nombre, scope)
    os.remove(destino)
    return {"ok": True}


@app.get("/documentos/pagina")
def pagina_documento(ref: str = Query(...), pagina: int = 1):
    """PNG de una pagina, para el visor que abre la cita en el punto exacto."""
    destino = _resolver(ref)
    total = pdfreader.num_paginas(destino)
    pagina = max(1, min(pagina, total))
    png = pdfreader.render_png(destino, pagina)
    return Response(content=png, media_type="image/png",
                    headers={"X-Total-Paginas": str(total),
                             "Cache-Control": "public, max-age=3600"})


@app.get("/documentos/info")
def info_documento(ref: str = Query(...)):
    destino = _resolver(ref)
    return {"nombre": os.path.basename(destino), "paginas": pdfreader.num_paginas(destino)}


# ---------- metricas ----------
@app.get("/metricas")
def get_metricas(carrera: Optional[str] = None, curso: Optional[str] = None):
    """
    Agregado y anonimo: texto de la consulta y fecha, nunca quien pregunto.
    Sin parametros devuelve el global; con carrera+curso, el de ese aula.
    """
    if carrera and curso:
        filas = metricas.listar(exact=rag.scope_curso(carrera, curso))
    elif carrera:
        filas = metricas.listar(prefix=carrera + "|")
    else:
        filas = metricas.listar()
    return metricas.resumen(filas)
