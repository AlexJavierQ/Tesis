# -*- coding: utf-8 -*-
"""
API REST del Asistente de Practicum (C3 - backend).
Cualquier frontend (la web de la U, una app, el Streamlit) la consume por HTTP.

Correr:  uvicorn api:app --reload
Docs interactivas:  http://localhost:8000/docs
"""
import os
import sqlite3
import datetime as dt
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import rag
import ingest

DB = os.path.join(os.path.dirname(__file__), "consultas.db")

app = FastAPI(title="API Asistente de Practicum", version="1.0")
# CORS abierto para que cualquier front pueda consumir la API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _log(pregunta, ok, fuentes):
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS consultas (ts TEXT, pregunta TEXT, respondida INTEGER, fuentes TEXT)")
    c.execute("INSERT INTO consultas VALUES (?,?,?,?)",
              (dt.datetime.now().strftime("%Y-%m-%d %H:%M"), pregunta, int(ok), " | ".join(fuentes)))
    c.commit(); c.close()


# ---------- modelos ----------
class Consulta(BaseModel):
    pregunta: str
    carrera: str
    curso: Optional[str] = None


# ---------- endpoints ----------
@app.get("/salud")
def salud():
    return {"ok": True, "modelo": rag.GEMINI_MODEL}


@app.get("/carreras")
def get_carreras():
    return rag.carreras()


@app.get("/carreras/{carrera}/cursos")
def get_cursos(carrera: str):
    return rag.cursos(carrera)


@app.post("/preguntar")
def preguntar(c: Consulta):
    """Pregunta al bot de una carrera (y opcionalmente un curso). Devuelve respuesta + citas."""
    scopes = rag.scopes_for(c.carrera, c.curso)
    r = rag.answer(c.pregunta, scopes=scopes)   # usa GEMINI_API_KEY del entorno
    _log(c.pregunta, r["con_respaldo"], r["fuentes"])
    return {
        "respuesta": r["respuesta"],
        "fuentes": r["fuentes"],
        "citas": r["citas"],
        "con_respaldo": r["con_respaldo"],
    }


@app.post("/documentos")
def subir_documento(
    carrera: str = Form(...),
    archivo: UploadFile = File(...),
    curso: Optional[str] = Form(None),
):
    """Sube un PDF como global (coordinacion) o de un curso (docente) e indexa al instante."""
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo PDF.")
    if curso:
        folder = rag.folder_curso(carrera, curso); scope = rag.scope_curso(carrera, curso)
    else:
        folder = rag.folder_global(carrera); scope = rag.scope_global(carrera)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, archivo.filename)
    with open(path, "wb") as f:
        f.write(archivo.file.read())
    n = ingest.add_pdf(path, scope)
    return {"ok": True, "archivo": archivo.filename, "scope": scope, "fragmentos": n}


@app.get("/metricas")
def metricas():
    """Agregado y anonimo: solo texto y fecha, nunca quien pregunto."""
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS consultas (ts TEXT, pregunta TEXT, respondida INTEGER, fuentes TEXT)")
    filas = c.execute("SELECT pregunta, respondida FROM consultas").fetchall()
    c.close()
    total = len(filas)
    con = sum(f[1] for f in filas)
    sin_respaldo = list(dict.fromkeys(f[0] for f in filas if not f[1]))
    return {"total": total, "con_respaldo": con,
            "pct_respaldo": round(100 * con / total) if total else 0,
            "sin_respaldo": sin_respaldo[:20]}
