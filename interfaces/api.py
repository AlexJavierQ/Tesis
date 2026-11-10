# -*- coding: utf-8 -*-
"""
API REST del Asistente de Practicum.

Es el UNICO backend. Las interfaces (React y widget) la consumen por HTTP.
Aqui no hay logica del RAG: solo se orquesta la llamada a los modulos del
nucleo, se validan permisos y se serializa la respuesta.

ROLES Y PERMISOS
  administrador -> configuracion del sistema (parametros), estructura
                   institucional (facultades y carreras), todos los usuarios
                   (asigna coordinadores a carreras), bitacora completa.
                   No gestiona documentos ni cursos.
  coordinacion  -> dentro de SUS carreras: cursos, asignacion de docentes,
                   reglamentos generales, usuarios estudiante/docente,
                   metricas de la carrera.
  docente       -> solo los cursos que tiene asignados: sube, versiona,
                   activa/desactiva documentos y ve sus metricas.
  estudiante    -> usa el chat (solo en sus carreras) y su propio historial.

Toda ruta exige sesion (token en el header Authorization, nunca en la URL),
salvo /login y /salud. El ambito (carrera, curso) se valida SIEMPRE aqui, en
el servidor: la interfaz solo oculta lo que cada rol no usa.

Se corre con:  uvicorn interfaces.api:app --reload
Docs interactivas:  http://localhost:8000/docs
"""
import os
import sys

# permite ejecutar este archivo: agrega la raiz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import config  # noqa: F401  # carga las keys ANTES que el motor

from typing import Optional, List, Literal
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from nucleo import (rag, ingest, vectorstore, pdfreader, metricas, auth, bd,
                    historial, parametros, memoria)

app = FastAPI(title="API Asistente de Practicum", version="6.0")

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

Rol = Literal["estudiante", "docente", "coordinacion", "administrador"]
ROLES_QUE_GESTIONA_COORD = ("estudiante", "docente")


# ---------- MODELOS de peticion/respuesta ----------
class Credenciales(BaseModel):
    usuario: str = Field(..., max_length=120)      # usuario o correo
    password: str = Field(..., max_length=200)


class Consulta(BaseModel):
    pregunta: str = Field(..., max_length=1000)
    carrera: str
    curso: Optional[str] = None
    # desde donde quiere la respuesta el estudiante (ver rag.modo_efectivo)
    modo: Optional[Literal["general", "curso", "ambos"]] = None
    conversacion_id: Optional[int] = None   # si viene y hay sesion, se guarda al historial


class UsuarioNuevo(BaseModel):
    usuario: str = Field(..., min_length=1, max_length=60)
    nombre: str = Field(..., min_length=1, max_length=120)
    correo: str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=200)
    rol: Rol
    carreras: List[str] = []


class UsuarioCambio(BaseModel):
    rol: Optional[Rol] = None
    carreras: Optional[List[str]] = None
    nombre: Optional[str] = Field(None, max_length=120)
    correo: Optional[str] = Field(None, max_length=120)
    nuevo_password: Optional[str] = Field(None, min_length=6, max_length=200)
    activo: Optional[bool] = None


class Estado(BaseModel):
    activo: bool


class Vigencia(BaseModel):
    vigencia: str = Field("", max_length=200)


class Docentes(BaseModel):
    usuarios: List[str]


class Valor(BaseModel):
    valor: str = Field(..., max_length=2000)


# ---------- utilidades de seguridad ----------
def _token(authorization):
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1]


def _sesion(authorization: str):
    """Extrae el usuario del header 'Authorization: Bearer <token>'."""
    return auth.usuario_de(_token(authorization))


def _exigir(authorization, *roles):
    """Devuelve el usuario si su rol esta en `roles`. Si no, 401/403."""
    usuario = _sesion(authorization)
    if not usuario:
        raise HTTPException(401, "Debes iniciar sesion.")
    if roles and usuario["rol"] not in roles:
        raise HTTPException(403, "No tienes permisos para esta accion.")
    return usuario


def _exigir_carrera(usuario, carrera):
    """Coordinacion y docentes solo trabajan en las carreras que tienen asignadas."""
    if carrera not in usuario["carreras"]:
        raise HTTPException(403, "No perteneces a esa carrera.")


def _exigir_ambito_docs(usuario, carrera, curso):
    """
    Quien puede tocar los documentos de un ambito:
      coordinacion -> reglamentos generales y cualquier curso de sus carreras
      docente      -> solo los cursos que tiene asignados (nunca los generales)
    """
    _exigir_carrera(usuario, carrera)
    if usuario["rol"] == "docente":
        if not curso:
            raise HTTPException(403, "Los reglamentos generales los gestiona la coordinacion.")
        if {"carrera": carrera, "curso": curso} not in usuario["cursos_asignados"]:
            raise HTTPException(403, "No tienes asignado ese curso.")


def _nombre_valido(nombre):
    nombre = (nombre or "").strip()
    if not nombre or "/" in nombre or "\\" in nombre or nombre.startswith(".") \
            or nombre.startswith("_"):
        raise HTTPException(400, "Nombre no valido.")
    return nombre


def _exigir_lectura_doc(usuario, d):
    """
    Quien puede LEER un documento (abrir la pagina que respalda una cita):
      estudiante y coordinacion -> los documentos de sus carreras
      docente                   -> los de los cursos que tiene asignados
      administrador             -> ninguno (no pertenece a carreras)
    """
    if d["carrera"] not in usuario["carreras"]:
        raise HTTPException(403, "No tienes acceso a ese documento.")
    if usuario["rol"] == "docente" and \
            {"carrera": d["carrera"], "curso": d["curso"]} not in usuario["cursos_asignados"]:
        raise HTTPException(403, "No tienes acceso a ese documento.")


# ==================== ESTRUCTURA ACADEMICA (leer: con sesion; crear: admin / coordinacion) ====================
@app.get("/salud")
def salud():
    """Estado del servicio."""
    return {
        "ok": True,
        "llm_disponible": config.hay_key(),
        "fragmentos_indexados": vectorstore.contar(),
    }


@app.get("/facultades")
def get_facultades(authorization: str = Header(None)):
    """Facultades con sus carreras. Solo administrador (estructura institucional)."""
    _exigir(authorization, "administrador")
    return bd.facultades()


@app.post("/facultades")
def crear_facultad(nombre: str = Form(...), authorization: str = Header(None)):
    """Crea una facultad. Solo administrador (estructura institucional)."""
    actor = _exigir(authorization, "administrador")
    nombre = _nombre_valido(nombre)
    try:
        bd.crear_facultad(nombre)
    except ValueError as e:
        raise HTTPException(409, str(e))
    bd.log("crear_facultad", nombre, actor["usuario"])
    return {"ok": True, "facultad": nombre}


@app.get("/carreras")
def get_carreras(authorization: str = Header(None)):
    """Carreras: el administrador las ve todas; los demas roles, solo las suyas."""
    usuario = _exigir(authorization)
    if usuario["rol"] == "administrador":
        return rag.carreras()
    return usuario["carreras"]


@app.get("/carreras/{carrera}/cursos")
def get_cursos(carrera: str, authorization: str = Header(None)):
    """Cursos de una carrera. Solo quien pertenece a ella (o el administrador)."""
    usuario = _exigir(authorization)
    if usuario["rol"] != "administrador":
        _exigir_carrera(usuario, carrera)
    return rag.cursos(carrera)


@app.post("/carreras")
def crear_carrera(nombre: str = Form(...), facultad: str = Form(bd.FACULTAD_POR_DEFECTO),
                  authorization: str = Header(None)):
    """
    Crea una carrera dentro de una facultad (en la BD) y su carpeta. Solo
    administrador; luego asigna la carrera a su coordinador desde Usuarios.
    """
    actor = _exigir(authorization, "administrador")
    nombre = _nombre_valido(nombre)
    try:
        bd.crear_carrera(nombre, facultad)
    except ValueError as e:
        raise HTTPException(409, str(e))
    os.makedirs(rag.carpeta_global(nombre), exist_ok=True)
    bd.log("crear_carrera", f"{nombre} ({facultad})", actor["usuario"])
    return {"ok": True, "carrera": nombre}


@app.post("/carreras/{carrera}/cursos")
def crear_curso(carrera: str, nombre: str = Form(...),
                authorization: str = Header(None)):
    """Crea un curso (en la BD) y su carpeta. Solo coordinacion de esa carrera."""
    actor = _exigir(authorization, "coordinacion")
    _exigir_carrera(actor, carrera)
    nombre = _nombre_valido(nombre)
    try:
        bd.crear_curso(carrera, nombre)
    except ValueError as e:
        raise HTTPException(409, str(e))
    os.makedirs(rag.carpeta_curso(carrera, nombre), exist_ok=True)
    bd.log("crear_curso", f"{carrera} / {nombre}", actor["usuario"])
    return {"ok": True, "curso": nombre}


@app.get("/carreras/{carrera}/cursos/{curso}/docentes")
def get_docentes_curso(carrera: str, curso: str, authorization: str = Header(None)):
    """Docentes asignados a un curso. Solo coordinacion de esa carrera."""
    actor = _exigir(authorization, "coordinacion")
    _exigir_carrera(actor, carrera)
    return bd.docentes_de_curso(carrera, curso)


@app.put("/carreras/{carrera}/cursos/{curso}/docentes")
def asignar_docentes_curso(carrera: str, curso: str, d: Docentes,
                           authorization: str = Header(None)):
    """Define que docentes dictan un curso (reemplaza la lista). Solo coordinacion."""
    actor = _exigir(authorization, "coordinacion")
    _exigir_carrera(actor, carrera)
    try:
        bd.asignar_docentes(carrera, curso, d.usuarios)
    except ValueError as e:
        raise HTTPException(400, str(e))
    bd.log("asignar_docentes", f"{carrera} / {curso}: {', '.join(d.usuarios) or '(ninguno)'}",
           actor["usuario"])
    return {"ok": True}


# ==================== AUTENTICACION ====================
@app.post("/login")
def api_login(cred: Credenciales):
    """Devuelve un token si las credenciales son correctas (usuario o correo)."""
    token = auth.login(cred.usuario, cred.password)
    if not token:
        bd.log("login_fallido", cred.usuario.strip()[:120])
        raise HTTPException(401, "Usuario o contrasena incorrectos.")
    usuario = auth.usuario_de(token)
    bd.log("login", "", usuario["usuario"])
    return {"token": token, "usuario": usuario}


@app.get("/me")
def api_me(authorization: str = Header(None)):
    """Devuelve el usuario actual segun el token."""
    return _exigir(authorization)


@app.post("/logout")
def api_logout(authorization: str = Header(None)):
    """Cierra la sesion."""
    usuario = _sesion(authorization)
    if usuario:
        auth.logout(_token(authorization))
        bd.log("logout", "", usuario["usuario"])
    return {"ok": True}


# ==================== GESTION DE USUARIOS (administrador y coordinacion) ====================
def _coord_puede_tocar(actor, objetivo):
    """
    La coordinacion solo gestiona estudiantes y docentes que compartan alguna
    de sus carreras. El administrador gestiona a todos.
    """
    if actor["rol"] == "administrador":
        return True
    return (objetivo["rol"] in ROLES_QUE_GESTIONA_COORD
            and bool(set(objetivo["carreras"]) & set(actor["carreras"])))


def _validar_alta_coord(actor, rol, carreras):
    """Lo que la coordinacion puede asignar: rol estudiante/docente y carreras propias."""
    if actor["rol"] == "administrador":
        return
    if rol and rol not in ROLES_QUE_GESTIONA_COORD:
        raise HTTPException(403, "La coordinacion solo gestiona estudiantes y docentes.")
    if carreras is not None and not set(carreras) <= set(actor["carreras"]):
        raise HTTPException(403, "Solo puedes asignar carreras que coordinas.")


@app.get("/usuarios")
def get_usuarios(authorization: str = Header(None)):
    """Lista de usuarios (sin passwords). Admin: todos. Coord: los de sus carreras."""
    actor = _exigir(authorization, "administrador", "coordinacion")
    return [u for u in auth.listar_usuarios()
            if u["usuario"] == actor["usuario"] or _coord_puede_tocar(actor, u)]


@app.post("/usuarios")
def crear_usuario_api(u: UsuarioNuevo, authorization: str = Header(None)):
    """Crea un usuario nuevo. Admin: cualquier rol. Coord: estudiante/docente."""
    actor = _exigir(authorization, "administrador", "coordinacion")
    _validar_alta_coord(actor, u.rol, u.carreras)
    try:
        auth.crear_usuario(u.usuario.strip(), u.nombre, u.correo, u.password, u.rol, u.carreras)
    except ValueError as e:
        raise HTTPException(400, str(e))
    bd.log("crear_usuario", f"{u.usuario.strip()} ({u.rol})", actor["usuario"])
    return {"ok": True, "usuario": u.usuario.strip()}


@app.put("/usuarios/{usuario}")
def actualizar_usuario_api(usuario: str, cambio: UsuarioCambio,
                           authorization: str = Header(None)):
    """
    Actualiza datos de un usuario.
    Protecciones: nadie puede cambiarse su propio rol ni desactivarse.
    """
    actor = _exigir(authorization, "administrador", "coordinacion")
    objetivo = auth.datos_de(usuario)
    if not objetivo:
        raise HTTPException(404, "Usuario no encontrado.")
    if actor["usuario"] == usuario:
        if cambio.rol and cambio.rol != actor["rol"]:
            raise HTTPException(400, "No puedes cambiar tu propio rol.")
        if cambio.activo is False:
            raise HTTPException(400, "No puedes desactivarte a ti mismo.")
    elif not _coord_puede_tocar(actor, objetivo):
        raise HTTPException(403, "No puedes gestionar a ese usuario.")
    _validar_alta_coord(actor, cambio.rol, cambio.carreras)
    carreras = cambio.carreras
    if actor["rol"] == "coordinacion" and actor["usuario"] != usuario:
        # la coordinacion no altera lo que el usuario tiene en carreras ajenas
        ajenas = sorted(set(objetivo["carreras"]) - set(actor["carreras"]))
        if ajenas and any(v is not None for k, v in cambio.model_dump().items() if k != "carreras"):
            raise HTTPException(403, "Ese usuario tambien pertenece a otra carrera: solo "
                                     "puedes cambiar su pertenencia a las tuyas.")
        if carreras is not None:
            carreras = sorted(set(carreras) | set(ajenas))
    try:
        auth.actualizar_usuario(usuario, cambio.rol, carreras, cambio.nuevo_password,
                                cambio.activo, cambio.nombre, cambio.correo)
    except ValueError as e:
        raise HTTPException(400, str(e))
    campos = [k for k, v in cambio.model_dump().items() if v is not None]
    bd.log("editar_usuario", f"{usuario}: {', '.join(campos)}", actor["usuario"])
    return {"ok": True}


@app.delete("/usuarios/{usuario}")
def borrar_usuario_api(usuario: str, authorization: str = Header(None)):
    """Elimina un usuario. Nadie puede borrarse a si mismo."""
    actor = _exigir(authorization, "administrador", "coordinacion")
    if actor["usuario"] == usuario:
        raise HTTPException(400, "No puedes borrarte a ti mismo.")
    objetivo = auth.datos_de(usuario)
    if not objetivo:
        raise HTTPException(404, "Usuario no encontrado.")
    if not _coord_puede_tocar(actor, objetivo):
        raise HTTPException(403, "No puedes gestionar a ese usuario.")
    if actor["rol"] == "coordinacion" and set(objetivo["carreras"]) - set(actor["carreras"]):
        raise HTTPException(403, "Ese usuario tambien pertenece a otra carrera: "
                                 "retiralo de la tuya en lugar de eliminarlo.")
    auth.borrar_usuario(usuario)
    bd.log("borrar_usuario", usuario, actor["usuario"])
    return {"ok": True}


# ==================== CONSULTA V1 (estudiante autenticado) ====================
@app.post("/preguntar")
def preguntar(c: Consulta, authorization: str = Header(None)):
    """Responde con corpus autorizado; solo estudiantes con sesion valida en V1."""
    # V1: el chat es autenticado y se restringe a las carreras del estudiante.
    # El widget sin sesion es una extension FUERA del alcance V1.
    # La sesion y la carrera se validan ANTES que nada: sin permiso no se
    # revela ni siquiera si una carrera o un curso existen.
    usuario = _exigir(authorization, "estudiante")
    _exigir_carrera(usuario, c.carrera)

    if not c.pregunta.strip():
        raise HTTPException(400, "La pregunta esta vacia.")
    if c.carrera not in rag.carreras():
        raise HTTPException(404, "Carrera no encontrada.")
    if c.curso and c.curso not in rag.cursos(c.carrera):
        raise HTTPException(404, "Curso no encontrado.")
    if c.modo == "curso" and not c.curso:
        raise HTTPException(400, "Para responder desde un curso, elige el curso.")

    # Nunca tolerar de forma silenciosa un id de conversacion ajeno.
    # El chat no debe responder ni escribir datos bajo un hilo de otro usuario.
    if c.conversacion_id is not None and not historial.es_dueno(
            c.conversacion_id, usuario["usuario"]):
        raise HTTPException(403, "Esa conversacion no es tuya.")
    es_suya = c.conversacion_id is not None
    contexto = memoria.preparar(c.conversacion_id) if es_suya else None

    r = rag.responder(c.pregunta, c.carrera, c.curso, contexto, c.modo)
    # analitica minimizada: solo la categoria de la pregunta, sin texto ni
    # usuario. Los saludos y agradecimientos no son consultas: no se cuentan.
    if not r.get("social"):
        metricas.registrar(c.pregunta, r["con_respaldo"], c.carrera,
                           c.curso if r["modo"] != "general" else None, r["modo"])
    # cada cita guarda documento y VERSION usados (trazabilidad historica).
    # No se expone la ruta del archivo: la pagina se pide por documento y version.
    citas = [{"fuente": ci["fuente"], "pagina": ci["pagina"], "seccion": ci["seccion"],
              "documento_id": ci["documento_id"], "version": ci["version"]}
             for ci in r["citas"]]

    # persistencia del historial (solo si la conversacion es suya)
    if es_suya:
        historial.agregar_mensaje(c.conversacion_id, "user", c.pregunta)
        historial.agregar_mensaje(c.conversacion_id, "bot", r["respuesta"], citas)

    return {
        "respuesta": r["respuesta"],
        "con_respaldo": r["con_respaldo"],
        # True = el modelo no respondio y se muestran los fragmentos tal cual
        "degradado": r.get("degradado", False),
        "modo": r["modo"],
        # como entendio el sistema la pregunta (distinta si la memoria la reescribio)
        "pregunta_interpretada": r["pregunta_interpretada"],
        "citas": citas,
    }


# ==================== HISTORIAL DE CHAT (del usuario con sesion) ====================
@app.get("/conversaciones")
def listar_conversaciones(authorization: str = Header(None)):
    """Lista las conversaciones del usuario actual."""
    usuario = _exigir(authorization)
    return historial.conversaciones_de(usuario["usuario"])


@app.post("/conversaciones")
def crear_conversacion_api(titulo: str = Form(""), authorization: str = Header(None)):
    """Crea una conversacion nueva y devuelve su id. Solo estudiantes (el chat es suyo)."""
    usuario = _exigir(authorization, "estudiante")
    cid = historial.crear_conversacion(usuario["usuario"], titulo)
    return {"id": cid}


@app.get("/conversaciones/{cid}")
def ver_conversacion(cid: int, authorization: str = Header(None)):
    """Mensajes de una conversacion. Solo su dueno."""
    usuario = _exigir(authorization)
    if not historial.es_dueno(cid, usuario["usuario"]):
        raise HTTPException(403, "Esa conversacion no es tuya.")
    return historial.mensajes_de(cid)


@app.delete("/conversaciones/{cid}")
def borrar_conversacion_api(cid: int, authorization: str = Header(None)):
    """Borra una conversacion. Solo su dueno."""
    usuario = _exigir(authorization)
    if not historial.es_dueno(cid, usuario["usuario"]):
        raise HTTPException(403, "Esa conversacion no es tuya.")
    historial.borrar_conversacion(cid)
    return {"ok": True}


# ==================== DOCUMENTOS (coordinacion y docente) ====================
def _doc_gestionable(doc_id, actor):
    """Devuelve el documento si existe y el actor puede gestionar su ambito."""
    d = bd.documento_por_id(doc_id)
    if not d:
        raise HTTPException(404, "Documento no encontrado.")
    _exigir_ambito_docs(actor, d["carrera"], d["curso"])
    return d


def _ambito(d):
    return f"{d['carrera']}/{d['curso'] or 'global'}/{d['nombre']}"


@app.get("/documentos")
def listar_documentos(carrera: str, curso: Optional[str] = None,
                      authorization: str = Header(None)):
    """Documentos de un ambito (version vigente). Solo quien gestiona ese ambito."""
    actor = _exigir(authorization, "docente", "coordinacion")
    _exigir_ambito_docs(actor, carrera, curso)
    return [{"id": d["id"], "nombre": d["nombre"], "ref": d["ruta"], "vigencia": d["vigencia"],
             "activo": d["activo"], "version": d["version"], "versiones": d["versiones"],
             "fragmentos": d["fragmentos"], "subido_en": d["subido_en"]}
            for d in bd.documentos_de(carrera, curso)]


@app.post("/documentos")
def subir_documento(carrera: str = Form(...),
                    archivo: UploadFile = File(...),
                    curso: Optional[str] = Form(None),
                    authorization: str = Header(None)):
    """
    Sube un PDF y lo indexa. Si ya existe uno con el mismo nombre en ese
    ambito, se guarda como NUEVA VERSION (la anterior queda de respaldo).
    """
    actor = _exigir(authorization, "docente", "coordinacion")
    _exigir_ambito_docs(actor, carrera, curso)
    if curso and curso not in rag.cursos(carrera):
        raise HTTPException(404, "Curso no encontrado.")
    nombre = os.path.basename(archivo.filename or "")
    if not nombre.lower().endswith(".pdf") or nombre.startswith((".", "_")):
        raise HTTPException(400, "Solo se aceptan PDF.")
    contenido = archivo.file.read()
    if not contenido.startswith(b"%PDF"):
        raise HTTPException(400, "El archivo no es un PDF valido.")
    max_mb = parametros.obtener("max_pdf_mb")
    if len(contenido) > max_mb * 1024 * 1024:
        raise HTTPException(400, f"El PDF supera {max_mb} MB.")

    try:
        r = ingest.guardar_documento(carrera, curso, nombre, contenido, actor["usuario"])
    except ValueError as e:      # p. ej. PDF escaneado, sin texto
        raise HTTPException(400, str(e))
    bd.log("subir_documento", f"{carrera}/{curso or 'global'}/{nombre} v{r['version']}",
           actor["usuario"])
    return {"ok": True, "archivo": nombre, **r}


@app.get("/documentos/{doc_id}/versiones")
def versiones_documento(doc_id: int, authorization: str = Header(None)):
    """Historial de versiones de un documento."""
    actor = _exigir(authorization, "docente", "coordinacion")
    _doc_gestionable(doc_id, actor)
    return bd.versiones_de(doc_id)


@app.post("/documentos/{doc_id}/versiones/{numero}/restaurar")
def restaurar_version(doc_id: int, numero: int, authorization: str = Header(None)):
    """
    Vuelve a una version anterior como lo hace git (revert): crea una version
    NUEVA con el contenido de la elegida; no se borra ninguna.
    """
    actor = _exigir(authorization, "docente", "coordinacion")
    d = _doc_gestionable(doc_id, actor)
    try:
        r = ingest.restaurar_version(doc_id, numero, actor["usuario"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    bd.log("restaurar_documento", f"{_ambito(d)}: v{numero} -> v{r['version']}", actor["usuario"])
    return {"ok": True, **r}


@app.patch("/documentos/{doc_id}/estado")
def estado_documento(doc_id: int, e: Estado, authorization: str = Header(None)):
    """Activa o desactiva un documento (desactivado = el chat no lo usa)."""
    actor = _exigir(authorization, "docente", "coordinacion")
    d = _doc_gestionable(doc_id, actor)
    ingest.cambiar_estado(doc_id, e.activo)
    bd.log("activar_documento" if e.activo else "desactivar_documento", _ambito(d),
           actor["usuario"])
    return {"ok": True, "activo": e.activo}


@app.patch("/documentos/{doc_id}/vigencia")
def vigencia_documento(doc_id: int, v: Vigencia, authorization: str = Header(None)):
    """
    Periodo o vigencia de la fuente (p. ej. "Periodo abril-agosto 2024").
    El asistente la menciona al citar fechas o plazos de ese documento.
    """
    actor = _exigir(authorization, "docente", "coordinacion")
    d = _doc_gestionable(doc_id, actor)
    bd.cambiar_vigencia(doc_id, v.vigencia)
    bd.log("cambiar_vigencia", f"{_ambito(d)}: {v.vigencia.strip() or '(sin indicar)'}", actor["usuario"])
    return {"ok": True}


@app.delete("/documentos/{doc_id}")
def borrar_documento(doc_id: int, authorization: str = Header(None)):
    """
    Elimina un documento con todas sus versiones. Si alguna respuesta del chat
    lo cita, se rechaza (409): las citas deben poder abrir la version usada.
    """
    actor = _exigir(authorization, "docente", "coordinacion")
    d = _doc_gestionable(doc_id, actor)
    try:
        ingest.borrar_documento(doc_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    bd.log("borrar_documento", _ambito(d), actor["usuario"])
    return {"ok": True}


@app.get("/documentos/{doc_id}/versiones/{numero}/paginas/{pagina}")
def pagina_de_version(doc_id: int, numero: int, pagina: int,
                      authorization: str = Header(None)):
    """
    PNG de una pagina de una VERSION concreta de un documento (visor de citas).
    La cita trae documento y version, y el archivo se busca en el catalogo: asi
    se abre siempre la version que respaldo la respuesta, aunque despues se
    haya publicado otra. El cliente nunca envia rutas de archivo.
    """
    usuario = _exigir(authorization)
    v = bd.version_de(doc_id, numero)
    if not v:
        raise HTTPException(404, "Esa version del documento no existe.")
    _exigir_lectura_doc(usuario, v)
    destino = os.path.join(rag.DOCS, v["ruta"])
    if not os.path.exists(destino):
        raise HTTPException(404, "El archivo de esa version ya no esta disponible.")
    total = pdfreader.num_paginas(destino)
    if not 1 <= pagina <= total:
        raise HTTPException(404, f"Ese documento tiene {total} paginas.")
    png = pdfreader.render_png(destino, pagina)
    return Response(content=png, media_type="image/png",
                    headers={"X-Total-Paginas": str(total),
                             "Cache-Control": "private, max-age=3600"})


# ==================== METRICAS ====================
@app.get("/metricas")
def get_metricas(carrera: Optional[str] = None,
                 curso: Optional[str] = None,
                 authorization: str = Header(None)):
    """
    Agregados por categoria (no hay preguntas ni usuarios: no se almacenan).
      - Coordinacion: una carrera suya completa, o uno de sus cursos.
      - Docente: solo un curso que tenga asignado.
    """
    usuario = _exigir(authorization, "docente", "coordinacion")
    carrera = carrera or usuario["carrera"]
    _exigir_carrera(usuario, carrera)
    if usuario["rol"] == "docente":
        if not curso:
            raise HTTPException(400, "El docente debe indicar un curso.")
        _exigir_ambito_docs(usuario, carrera, curso)
    elif curso and curso not in rag.cursos(carrera):
        raise HTTPException(404, "Curso no encontrado.")
    return metricas.resumen(carrera, curso)


# ==================== CONFIGURACION DEL SISTEMA (solo administrador) ====================
@app.get("/parametros")
def get_parametros(authorization: str = Header(None)):
    """Parametros configurables agrupados por area, con descripcion, rango y ultimo cambio."""
    _exigir(authorization, "administrador")
    return parametros.por_areas()


@app.put("/parametros/{clave}")
def put_parametro(clave: str, v: Valor, authorization: str = Header(None)):
    """Cambia un parametro (se valida tipo y rango). Queda en la bitacora."""
    actor = _exigir(authorization, "administrador")
    try:
        anterior = parametros.actualizar(clave, v.valor, actor["usuario"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    bd.log("cambiar_parametro", f"{clave}: {anterior[:60]} -> {v.valor.strip()[:60]}",
           actor["usuario"])
    return {"ok": True}


# ==================== BITACORA (solo administrador) ====================
@app.get("/logs")
def get_logs(limite: int = Query(200, ge=1, le=1000), authorization: str = Header(None)):
    """Ultimas acciones registradas en el sistema (quien, que, cuando)."""
    _exigir(authorization, "administrador")
    return bd.logs(limite)
