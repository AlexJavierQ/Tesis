# -*- coding: utf-8 -*-
"""
API REST del Asistente de Practicum.

Es el UNICO backend. Las tres interfaces (Streamlit, React, widget) la
consumen por HTTP. Aqui no hay logica del RAG: solo se orquesta la llamada
a los modulos del nucleo y se serializa la respuesta.

Se corre con:  uvicorn interfaces.api:app --reload
Docs interactivas:  http://localhost:8000/docs
"""
import os
import sys

# permite ejecutar este archivo: agrega la raiz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import config  # noqa: F401  # carga las keys ANTES que el motor

from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from nucleo import rag, ingest, vectorstore, pdfreader, metricas, auth

app = FastAPI(title="API Asistente de Practicum", version="3.0")

# CORS: origenes permitidos. En desarrollo el front corre en otro puerto.
ORIGENES = [o for o in os.environ.get("CORS_ORIGINS", "").split(",") if o] or [
    "http://localhost:5173", "http://127.0.0.1:5173",   # React (Vite)
    "http://localhost:5500", "http://127.0.0.1:5500",   # widget demo
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- MODELOS de peticion/respuesta ----------
class Credenciales(BaseModel):
    usuario: str
    password: str


class Consulta(BaseModel):
    pregunta: str
    carrera: str
    curso: Optional[str] = None


class UsuarioNuevo(BaseModel):
    usuario: str
    password: str
    rol: str
    carrera: str


class UsuarioCambio(BaseModel):
    rol: Optional[str] = None
    carrera: Optional[str] = None
    nuevo_password: Optional[str] = None


# ---------- utilidades de seguridad ----------
def _sesion(authorization: str):
    """Extrae el usuario del header 'Authorization: Bearer <token>'."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return auth.usuario_de(authorization.split(" ", 1)[1])


def _exigir(authorization, *roles):
    """Devuelve el usuario si su rol esta en `roles`. Si no, 401/403."""
    usuario = _sesion(authorization)
    if not usuario:
        raise HTTPException(401, "Debes iniciar sesion.")
    if roles and usuario["rol"] not in roles:
        raise HTTPException(403, "No tienes permisos para esta accion.")
    return usuario


def _resolver_ruta(ref):
    """
    Convierte una ref relativa (viene del cliente) en una ruta absoluta,
    verificando que caiga DENTRO de datos/docs/. Sin esto, un '../../..'
    en la ref serviria cualquier archivo del disco.
    """
    destino = os.path.abspath(os.path.join(rag.DOCS, ref))
    raiz = os.path.abspath(rag.DOCS)
    if os.path.commonpath([destino, raiz]) != raiz:
        raise HTTPException(400, "Ruta no permitida.")
    if not os.path.exists(destino):
        raise HTTPException(404, "Documento no encontrado.")
    return destino


# ==================== ENDPOINTS PUBLICOS ====================
@app.get("/salud")
def salud():
    """Estado del servicio."""
    return {
        "ok": True,
        "llm_disponible": config.hay_key(),
        "fragmentos_indexados": vectorstore.contar(),
    }


@app.get("/carreras")
def get_carreras():
    return rag.carreras()


@app.get("/carreras/{carrera}/cursos")
def get_cursos(carrera: str):
    return rag.cursos(carrera)


@app.post("/carreras/{carrera}/cursos")
def crear_curso(carrera: str, nombre: str = Form(...),
                authorization: str = Header(None)):
    """Crea la carpeta de un curso nuevo. Solo docente o coordinacion."""
    _exigir(authorization, "docente", "coordinacion")
    nombre = nombre.strip()
    if not nombre or "/" in nombre or "\\" in nombre or nombre.startswith("."):
        raise HTTPException(400, "Nombre de curso no valido.")
    carpeta = rag.carpeta_curso(carrera, nombre)
    if os.path.isdir(carpeta):
        raise HTTPException(409, "Ese curso ya existe.")
    os.makedirs(carpeta, exist_ok=True)
    return {"ok": True, "curso": nombre}


# ==================== AUTENTICACION ====================
@app.post("/login")
def api_login(cred: Credenciales):
    """Devuelve un token si las credenciales son correctas."""
    token = auth.login(cred.usuario, cred.password)
    if not token:
        raise HTTPException(401, "Usuario o contrasena incorrectos.")
    usuario = auth.usuario_de(token)
    return {"token": token, "usuario": usuario}


@app.get("/me")
def api_me(authorization: str = Header(None)):
    """Devuelve el usuario actual segun el token."""
    return _exigir(authorization)


@app.post("/logout")
def api_logout(authorization: str = Header(None)):
    """Cierra la sesion."""
    if authorization and authorization.lower().startswith("bearer "):
        auth.logout(authorization.split(" ", 1)[1])
    return {"ok": True}


# ==================== GESTION DE USUARIOS (solo coordinacion) ====================
@app.get("/usuarios")
def get_usuarios(authorization: str = Header(None)):
    """Lista todos los usuarios (sin passwords). Solo coordinacion."""
    _exigir(authorization, "coordinacion")
    return auth.listar_usuarios()


@app.post("/usuarios")
def crear_usuario_api(u: UsuarioNuevo, authorization: str = Header(None)):
    """Crea un usuario nuevo. Solo coordinacion."""
    _exigir(authorization, "coordinacion")
    if not u.usuario.strip() or not u.password.strip():
        raise HTTPException(400, "Usuario y contrasena obligatorios.")
    try:
        auth.crear_usuario(u.usuario.strip(), u.password, u.rol, u.carrera.strip())
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "usuario": u.usuario.strip()}


@app.put("/usuarios/{usuario}")
def actualizar_usuario_api(usuario: str, cambio: UsuarioCambio,
                           authorization: str = Header(None)):
    """
    Actualiza rol, carrera y/o password de un usuario. Solo coordinacion.
    Protecciones: coord no puede cambiar su propio rol (evita quedarse sin coord).
    """
    actor = _exigir(authorization, "coordinacion")
    if actor["usuario"] == usuario and cambio.rol and cambio.rol != "coordinacion":
        raise HTTPException(400, "No puedes cambiar tu propio rol.")
    try:
        auth.actualizar_usuario(usuario, cambio.rol, cambio.carrera, cambio.nuevo_password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.delete("/usuarios/{usuario}")
def borrar_usuario_api(usuario: str, authorization: str = Header(None)):
    """Elimina un usuario. Solo coordinacion. No puede borrarse a si mismo."""
    actor = _exigir(authorization, "coordinacion")
    if actor["usuario"] == usuario:
        raise HTTPException(400, "No puedes borrarte a ti mismo.")
    auth.borrar_usuario(usuario)
    return {"ok": True}


# ==================== CONSULTA (publica: para el widget del portal) ====================
@app.post("/preguntar")
def preguntar(c: Consulta):
    """Pregunta al asistente. Publica: el widget del portal puede llamar sin login."""
    if not c.pregunta.strip():
        raise HTTPException(400, "La pregunta esta vacia.")
    r = rag.responder(c.pregunta, c.carrera, c.curso)
    scope_registro = f"{c.carrera}|curso:{c.curso}" if c.curso else f"{c.carrera}|global"
    metricas.registrar(c.pregunta, r["con_respaldo"], scope_registro)
    # convertimos las citas a un formato con `ref` (ruta relativa lista para el visor)
    return {
        "respuesta": r["respuesta"],
        "con_respaldo": r["con_respaldo"],
        "citas": [{"fuente": ci["fuente"], "pagina": ci["pagina"], "ref": ci["path"]}
                  for ci in r["citas"]],
    }


# ==================== DOCUMENTOS ====================
@app.get("/documentos")
def listar_documentos(carrera: str, curso: Optional[str] = None,
                      authorization: str = Header(None)):
    """Lista los PDF de un ambito. Requiere sesion."""
    _exigir(authorization)
    carpeta = rag.carpeta_curso(carrera, curso) if curso else rag.carpeta_global(carrera)
    if not os.path.isdir(carpeta):
        return []
    salida = []
    for nombre in sorted(os.listdir(carpeta)):
        if nombre.lower().endswith(".pdf"):
            p = os.path.join(carpeta, nombre)
            rel = os.path.relpath(p, rag.DOCS).replace("\\", "/")
            salida.append({"nombre": nombre, "ref": rel,
                           "paginas": pdfreader.num_paginas(p)})
    return salida


@app.post("/documentos")
def subir_documento(carrera: str = Form(...),
                    archivo: UploadFile = File(...),
                    curso: Optional[str] = Form(None),
                    authorization: str = Header(None)):
    """Sube un PDF y lo indexa. Solo docente/coordinacion."""
    _exigir(authorization, "docente", "coordinacion")
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan PDF.")
    nombre = os.path.basename(archivo.filename)
    if curso:
        carpeta, scope = rag.carpeta_curso(carrera, curso), f"{carrera}|curso:{curso}"
    else:
        carpeta, scope = rag.carpeta_global(carrera), f"{carrera}|global"
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, nombre)
    with open(destino, "wb") as f:
        f.write(archivo.file.read())
    n = ingest.indexar_pdf(destino, scope)
    return {"ok": True, "archivo": nombre, "fragmentos": n}


@app.delete("/documentos")
def borrar_documento(carrera: str, nombre: str, curso: Optional[str] = None,
                     authorization: str = Header(None)):
    """Elimina un PDF. Solo docente/coordinacion."""
    _exigir(authorization, "docente", "coordinacion")
    scope = f"{carrera}|curso:{curso}" if curso else f"{carrera}|global"
    carpeta = rag.carpeta_curso(carrera, curso) if curso else rag.carpeta_global(carrera)
    destino = os.path.join(carpeta, os.path.basename(nombre))
    if not os.path.exists(destino):
        raise HTTPException(404, "Documento no encontrado.")
    ingest.borrar_documento(os.path.basename(nombre), scope)
    os.remove(destino)
    return {"ok": True}


@app.get("/documentos/pagina")
def pagina_documento(ref: str = Query(...), pagina: int = 1,
                     authorization: str = Header(None)):
    """PNG de una pagina del PDF (para el visor). Requiere sesion."""
    _exigir(authorization)
    destino = _resolver_ruta(ref)
    total = pdfreader.num_paginas(destino)
    pagina = max(1, min(pagina, total))
    png = pdfreader.render_png(destino, pagina)
    return Response(content=png, media_type="image/png",
                    headers={"X-Total-Paginas": str(total),
                             "Cache-Control": "public, max-age=3600"})


@app.get("/documentos/info")
def info_documento(ref: str = Query(...), authorization: str = Header(None)):
    """Info del PDF (numero de paginas)."""
    _exigir(authorization)
    destino = _resolver_ruta(ref)
    return {"nombre": os.path.basename(destino), "paginas": pdfreader.num_paginas(destino)}


# ==================== METRICAS ====================
@app.get("/metricas")
def get_metricas(carrera: Optional[str] = None,
                 curso: Optional[str] = None,
                 authorization: str = Header(None)):
    """
    Agregados anonimos.
      - Coordinacion: puede ver todo (sin filtro), o su carrera, o un curso.
      - Docente: solo puede ver metricas de un curso concreto (el suyo).
      - Estudiante: no.
    """
    usuario = _exigir(authorization, "docente", "coordinacion")
    if usuario["rol"] == "docente" and not curso:
        raise HTTPException(400, "El docente debe indicar un curso.")
    # el docente solo consulta cursos de su propia carrera
    if usuario["rol"] == "docente":
        carrera = usuario["carrera"]

    if curso and carrera:
        filas = metricas.listar(prefijo=f"{carrera}|curso:{curso}")
    elif carrera:
        filas = metricas.listar(prefijo=carrera + "|")
    else:
        filas = metricas.listar()
    return metricas.resumen(filas)
