# -*- coding: utf-8 -*-
"""
Pruebas V1 de autorizacion, citas, analitica, integridad y migracion.

Ejecutar desde la raiz:
    python -m unittest pruebas.test_v1_seguridad -v

Todo ocurre en una carpeta de datos TEMPORAL (pruebas/aislado.py) con datos
sinteticos: dos carreras, tres cursos y usuarios de cada rol. No se llama al
modelo de lenguaje (rag.responder se sustituye) ni al modelo de embeddings (el
indice vectorial se sustituye): aqui se prueba la API, los permisos y la base
de datos. La recuperacion real se prueba en verificar.py y pruebas.integridad.

Requisitos que cubre: RF-01, RF-02, RF-06, RF-12, RF-13, RF-15, RF-17, RF-19,
RF-21, RF-22; RNF-03, RNF-04 y RNF-09.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from pruebas import aislado

DATOS = aislado.preparar()

import fitz  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from interfaces.api import app  # noqa: E402
from nucleo import auth, bd, categorias, ingest, metricas  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAVE = "clave-de-prueba-2026"
A, B = "computacion", "electronica"            # dos carreras
P1, P2, PE = "Practicum 1", "Practicum 2", "Practicum E"

cl = TestClient(app)
DOC = {}        # nombre corto -> id de documento
_parches = []


def pdf(titulo, cuerpo, paginas=1):
    """PDF sintetico con texto seleccionable (el que exige la ingesta)."""
    doc = fitz.open()
    for n in range(1, paginas + 1):
        pagina = doc.new_page()
        pagina.insert_textbox(fitz.Rect(60, 60, 540, 780),
                              f"{titulo} (pagina {n})\n\n" + (cuerpo + " ") * max(1, 900 // len(cuerpo)),
                              fontsize=11)
    return doc.tobytes()


def sesion(usuario):
    r = cl.post("/login", json={"usuario": usuario, "password": CLAVE})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def respuesta_rag(citas=(), con_respaldo=True, modo="general", **extra):
    """Lo que devolveria rag.responder, sin llamar al modelo."""
    return {"respuesta": "Respuesta sintetica de prueba.", "con_respaldo": con_respaldo,
            "modo": modo, "pregunta_interpretada": "pregunta",
            "citas": [{"fuente": "x.pdf", "pagina": p, "seccion": "Seccion", "documento_id": d,
                       "version": v, "path": "ruta/interna.pdf"} for d, v, p in citas], **extra}


def preguntar(cabecera, pregunta, carrera=A, curso=None, modo="general", conversacion_id=None,
              **rag_kw):
    with patch("nucleo.rag.responder", return_value=respuesta_rag(modo=modo, **rag_kw)) as mock:
        r = cl.post("/preguntar", headers=cabecera, json={
            "pregunta": pregunta, "carrera": carrera, "curso": curso, "modo": modo,
            "conversacion_id": conversacion_id})
    return r, mock


def setUpModule():
    assert os.path.abspath(bd.DB).startswith(os.path.abspath(DATOS)), "la prueba no esta aislada"
    # el indice vectorial y la memoria conversacional no se prueban aqui
    for objetivo in ("nucleo.ingest.vectorstore", "interfaces.api.memoria.preparar"):
        p = patch(objetivo, MagicMock(return_value=None) if objetivo.endswith("preparar") else MagicMock())
        p.start()
        _parches.append(p)

    bd.crear_carrera(B)
    for carrera, curso in ((A, P1), (A, P2), (B, PE)):
        bd.crear_curso(carrera, curso)
    usuarios = [
        ("est_a", "estudiante", [A]), ("est_a2", "estudiante", [A]), ("est_b", "estudiante", [B]),
        ("doc_a1", "docente", [A]), ("doc_a2", "docente", [A]), ("doc_b", "docente", [B]),
        ("coord_a", "coordinacion", [A]), ("coord_b", "coordinacion", [B]),
        ("admin_t", "administrador", []),
    ]
    for usuario, rol, carreras in usuarios:
        auth.crear_usuario(usuario, f"Prueba {usuario}", f"{usuario}@prueba.local", CLAVE, rol, carreras)
    bd.asignar_docentes(A, P1, ["doc_a1"])
    bd.asignar_docentes(A, P2, ["doc_a2"])
    bd.asignar_docentes(B, PE, ["doc_b"])

    cuerpo = "El practicum exige horas de practica, informes y evidencias segun el reglamento."
    for clave, carrera, curso, nombre in (("general_a", A, None, "reglamento.pdf"),
                                          ("curso_p1", A, P1, "guia_p1.pdf"),
                                          ("curso_p2", A, P2, "guia_p2.pdf"),
                                          ("general_b", B, None, "reglamento_b.pdf")):
        ingest.guardar_documento(carrera, curso, nombre, pdf(f"Documento {clave} version 1", cuerpo, 2))
        DOC[clave] = bd.documento(carrera, curso, nombre)["id"]


def tearDownModule():
    for p in _parches:
        p.stop()


# ============================== AUTORIZACION ==============================
class PruebasAutorizacion(unittest.TestCase):
    """RNF-03: cada ruta exige sesion, rol y ambito (carrera / curso / dueno)."""

    def test_sin_sesion_todo_devuelve_401(self):
        rutas = [("get", "/facultades"), ("get", "/carreras"), ("get", f"/carreras/{A}/cursos"),
                 ("get", "/me"), ("get", "/usuarios"), ("get", "/conversaciones"),
                 ("get", f"/documentos?carrera={A}"), ("get", "/metricas"), ("get", "/parametros"),
                 ("get", "/logs"), ("get", f"/documentos/{DOC['general_a']}/versiones"),
                 ("get", f"/documentos/{DOC['general_a']}/versiones/1/paginas/1"),
                 ("delete", f"/documentos/{DOC['general_a']}"), ("post", "/conversaciones")]
        for metodo, ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(getattr(cl, metodo)(ruta).status_code, 401)
        r, mock = preguntar({}, "¿Cuántas horas?")
        self.assertEqual(r.status_code, 401)
        mock.assert_not_called()

    def test_el_token_en_la_url_no_sirve(self):
        token = sesion("coord_a")["Authorization"].split(" ", 1)[1]
        for ruta in (f"/metricas?carrera={A}", f"/documentos/{DOC['general_a']}/versiones/1/paginas/1?x=1"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cl.get(f"{ruta}&token={token}&authorization={token}").status_code, 401)

    def test_estudiante_solo_usa_el_chat_de_su_carrera(self):
        es = sesion("est_a")
        for ruta in (f"/documentos?carrera={A}", f"/metricas?carrera={A}", "/usuarios",
                     "/facultades", "/parametros", "/logs", f"/carreras/{B}/cursos"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cl.get(ruta, headers=es).status_code, 403)
        self.assertEqual(cl.get("/carreras", headers=es).json(), [A])
        self.assertEqual(cl.get(f"/carreras/{A}/cursos", headers=es).json(), [P1, P2])
        r, mock = preguntar(es, "¿Cuántas horas?", carrera=B)
        self.assertEqual(r.status_code, 403)
        mock.assert_not_called()

    def test_solo_el_estudiante_pregunta(self):
        for usuario in ("doc_a1", "coord_a", "admin_t"):
            with self.subTest(usuario=usuario):
                r, mock = preguntar(sesion(usuario), "¿Cuántas horas?")
                self.assertEqual(r.status_code, 403)
                mock.assert_not_called()
                self.assertEqual(cl.post("/conversaciones", headers=sesion(usuario)).status_code, 403)

    def test_conversacion_ajena_inaccesible(self):
        dueno, otro = sesion("est_a"), sesion("est_a2")
        cid = cl.post("/conversaciones", data={"titulo": "privada"}, headers=dueno).json()["id"]
        r, _ = preguntar(dueno, "¿Qué evidencias presento?", conversacion_id=cid)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(cl.get(f"/conversaciones/{cid}", headers=otro).status_code, 403)
        self.assertEqual(cl.delete(f"/conversaciones/{cid}", headers=otro).status_code, 403)
        r, mock = preguntar(otro, "y eso?", conversacion_id=cid)
        self.assertEqual(r.status_code, 403)
        mock.assert_not_called()
        self.assertNotIn(cid, [c["id"] for c in cl.get("/conversaciones", headers=otro).json()])
        self.assertEqual(len(cl.get(f"/conversaciones/{cid}", headers=dueno).json()), 2)

    def test_docente_solo_gestiona_sus_cursos(self):
        do = sesion("doc_a1")
        self.assertEqual(cl.get("/documentos", params={"carrera": A, "curso": P1}, headers=do).status_code, 200)
        self.assertEqual(cl.get("/documentos", params={"carrera": A, "curso": P2}, headers=do).status_code, 403)
        self.assertEqual(cl.get("/documentos", params={"carrera": A}, headers=do).status_code, 403)
        self.assertEqual(cl.get("/documentos", params={"carrera": B, "curso": PE}, headers=do).status_code, 403)
        ajeno = DOC["curso_p2"]
        intentos = [("get", f"/documentos/{ajeno}/versiones", {}),
                    ("post", f"/documentos/{ajeno}/versiones/1/restaurar", {}),
                    ("patch", f"/documentos/{ajeno}/estado", {"json": {"activo": False}}),
                    ("patch", f"/documentos/{ajeno}/vigencia", {"json": {"vigencia": "x"}}),
                    ("delete", f"/documentos/{ajeno}", {}),
                    ("get", f"/documentos/{ajeno}/versiones/1/paginas/1", {}),
                    ("get", f"/documentos/{DOC['general_a']}/versiones/1/paginas/1", {})]
        for metodo, ruta, kw in intentos:
            with self.subTest(ruta=ruta, metodo=metodo):
                self.assertEqual(getattr(cl, metodo)(ruta, headers=do, **kw).status_code, 403)
        r = cl.post("/documentos", data={"carrera": A, "curso": P2}, headers=do,
                    files={"archivo": ("intruso.pdf", pdf("Intruso", "texto " * 40), "application/pdf")})
        self.assertEqual(r.status_code, 403)
        self.assertIsNone(bd.documento(A, P2, "intruso.pdf"))
        self.assertTrue(bd.documento_por_id(ajeno)["activo"])
        self.assertEqual(cl.put(f"/carreras/{A}/cursos/{P1}/docentes", headers=do,
                                json={"usuarios": ["doc_a1", "doc_a2"]}).status_code, 403)
        self.assertEqual(cl.get("/usuarios", headers=do).status_code, 403)
        # sus propios cursos si: metricas y pagina del documento de su curso
        self.assertEqual(cl.get("/metricas", params={"carrera": A, "curso": P1}, headers=do).status_code, 200)
        self.assertEqual(cl.get("/metricas", params={"carrera": A, "curso": P2}, headers=do).status_code, 403)
        self.assertEqual(cl.get("/metricas", params={"carrera": A}, headers=do).status_code, 400)
        self.assertEqual(cl.get(f"/documentos/{DOC['curso_p1']}/versiones/1/paginas/1", headers=do).status_code, 200)

    def test_docente_sube_un_pdf_a_su_curso_y_queda_indexado(self):
        do = sesion("doc_a1")
        r = cl.post("/documentos", data={"carrera": A, "curso": P1}, headers=do,
                    files={"archivo": ("silabo.pdf", pdf("Silabo", "contenido del curso " * 20), "application/pdf")})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["version"], 1)
        self.assertGreater(r.json()["fragmentos"], 0)
        self.assertIn("silabo.pdf", [d["nombre"] for d in cl.get(
            "/documentos", params={"carrera": A, "curso": P1}, headers=do).json()])
        malo = cl.post("/documentos", data={"carrera": A, "curso": P1}, headers=do,
                       files={"archivo": ("vacio.pdf", b"%PDF-1.4 nada", "application/pdf")})
        self.assertEqual(malo.status_code, 400)
        self.assertIsNone(bd.documento(A, P1, "vacio.pdf"))

    def test_coordinacion_no_sale_de_su_carrera(self):
        co = sesion("coord_a")
        self.assertEqual(cl.get("/documentos", params={"carrera": A}, headers=co).status_code, 200)
        self.assertEqual(cl.get("/metricas", params={"carrera": A}, headers=co).status_code, 200)
        self.assertEqual(cl.get("/metricas", params={"carrera": A, "curso": "no existe"}, headers=co).status_code, 404)
        intentos = [("get", "/documentos", {"params": {"carrera": B}}),
                    ("get", "/metricas", {"params": {"carrera": B}}),
                    ("get", "/metricas", {"params": {"carrera": B, "curso": PE}}),
                    ("get", f"/carreras/{B}/cursos", {}),
                    ("post", f"/carreras/{B}/cursos", {"data": {"nombre": "intruso"}}),
                    ("get", f"/carreras/{B}/cursos/{PE}/docentes", {}),
                    ("put", f"/carreras/{B}/cursos/{PE}/docentes", {"json": {"usuarios": []}}),
                    ("delete", f"/documentos/{DOC['general_b']}", {}),
                    ("get", f"/documentos/{DOC['general_b']}/versiones/1/paginas/1", {}),
                    ("get", "/facultades", {}), ("get", "/parametros", {}), ("get", "/logs", {})]
        for metodo, ruta, kw in intentos:
            with self.subTest(ruta=ruta, metodo=metodo):
                self.assertEqual(getattr(cl, metodo)(ruta, headers=co, **kw).status_code, 403)
        self.assertEqual(cl.get("/carreras", headers=co).json(), [A])
        visibles = {u["usuario"] for u in cl.get("/usuarios", headers=co).json()}
        self.assertIn("est_a", visibles)
        self.assertFalse(visibles & {"est_b", "doc_b", "coord_b", "admin_t"})
        nuevo = {"usuario": "x1", "nombre": "X", "correo": "x1@prueba.local", "password": CLAVE}
        self.assertEqual(cl.post("/usuarios", headers=co, json={**nuevo, "rol": "estudiante", "carreras": [B]}).status_code, 403)
        self.assertEqual(cl.post("/usuarios", headers=co, json={**nuevo, "rol": "coordinacion", "carreras": [A]}).status_code, 403)
        self.assertEqual(cl.delete("/usuarios/est_b", headers=co).status_code, 403)
        # no puede asignar a un curso suyo a un docente de otra carrera
        self.assertEqual(cl.put(f"/carreras/{A}/cursos/{P1}/docentes", headers=co,
                                json={"usuarios": ["doc_b"]}).status_code, 400)
        self.assertEqual(bd.docentes_de_curso(A, P1), ["doc_a1"])

    def test_coordinacion_no_altera_lo_de_otra_carrera_en_un_usuario_compartido(self):
        auth.crear_usuario("est_ab", "Compartido", "est_ab@prueba.local", CLAVE, "estudiante", [A, B])
        co = sesion("coord_a")
        self.assertEqual(cl.delete("/usuarios/est_ab", headers=co).status_code, 403)
        self.assertEqual(cl.put("/usuarios/est_ab", headers=co, json={"nuevo_password": "otra-clave-1"}).status_code, 403)
        self.assertEqual(cl.put("/usuarios/est_ab", headers=co, json={"activo": False}).status_code, 403)
        # si puede retirarlo de SU carrera; la pertenencia a la otra se conserva
        self.assertEqual(cl.put("/usuarios/est_ab", headers=co, json={"carreras": []}).status_code, 200)
        self.assertEqual(auth.datos_de("est_ab")["carreras"], [B])
        self.assertIsNotNone(auth.login("est_ab", CLAVE))

    def test_administrador_no_ve_documentos_ni_metricas(self):
        ad = sesion("admin_t")
        for ruta in (f"/documentos?carrera={A}", f"/metricas?carrera={A}",
                     f"/documentos/{DOC['general_a']}/versiones/1/paginas/1"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cl.get(ruta, headers=ad).status_code, 403)
        todas = cl.get("/carreras", headers=ad).json()
        self.assertEqual(todas, bd.carreras())
        self.assertTrue({A, B} <= set(todas))
        self.assertIn(PE, cl.get(f"/carreras/{B}/cursos", headers=ad).json())

    def test_retirar_la_asignacion_revoca_el_acceso(self):
        bd.crear_curso(A, "Temporal")
        bd.asignar_docentes(A, "Temporal", ["doc_a2"])
        do = sesion("doc_a2")
        ruta = {"carrera": A, "curso": "Temporal"}
        self.assertEqual(cl.get("/documentos", params=ruta, headers=do).status_code, 200)
        r = cl.put(f"/carreras/{A}/cursos/Temporal/docentes", headers=sesion("coord_a"), json={"usuarios": []})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(cl.get("/documentos", params=ruta, headers=do).status_code, 403)
        self.assertEqual(cl.get("/metricas", params=ruta, headers=do).status_code, 403)

    def test_sesion_revocada_al_desactivar_la_cuenta(self):
        auth.crear_usuario("est_baja", "Baja", "est_baja@prueba.local", CLAVE, "estudiante", [A])
        es = sesion("est_baja")
        self.assertEqual(cl.get("/me", headers=es).status_code, 200)
        self.assertEqual(cl.put("/usuarios/est_baja", headers=sesion("admin_t"), json={"activo": False}).status_code, 200)
        self.assertEqual(cl.get("/me", headers=es).status_code, 401)
        self.assertEqual(cl.post("/login", json={"usuario": "est_baja", "password": CLAVE}).status_code, 401)


# ============================== CITAS ==============================
class PruebasCitas(unittest.TestCase):
    """RF-06, RF-12, RF-15 y RNF-09: la cita abre la version exacta que se uso."""

    def test_cita_enlazada_a_la_version_y_visible_solo_con_permiso(self):
        es = sesion("est_a")
        doc = DOC["general_a"]
        cid = cl.post("/conversaciones", data={"titulo": "citas"}, headers=es).json()["id"]
        r, _ = preguntar(es, "¿Qué exige el reglamento?", conversacion_id=cid, citas=[(doc, 1, 2)])
        self.assertEqual(r.status_code, 200, r.text)
        cita = r.json()["citas"][0]
        self.assertEqual((cita["documento_id"], cita["version"], cita["pagina"]), (doc, 1, 2))
        self.assertFalse({"ref", "path", "ruta"} & set(cita), "la respuesta no expone rutas de archivo")

        # en la base: clave foranea a la version exacta
        with bd.transaccion() as c:
            filas = c.execute("""SELECT v.documento_id, v.numero, cm.pagina FROM citas_mensaje cm
                                 JOIN mensajes m ON m.id = cm.mensaje_id
                                 JOIN documento_versiones v ON v.id = cm.documento_version_id
                                 WHERE m.conversacion_id=?""", (cid,)).fetchall()
        self.assertEqual(filas, [(doc, 1, 2)])
        guardada = cl.get(f"/conversaciones/{cid}", headers=es).json()[1]["citas"][0]
        self.assertEqual(guardada, {"fuente": "reglamento.pdf", "pagina": 2, "seccion": "Seccion",
                                    "documento_id": doc, "version": 1})

        ruta = f"/documentos/{doc}/versiones/1/paginas/2"
        ok = cl.get(ruta, headers=es)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.headers["content-type"], "image/png")
        self.assertTrue(ok.content.startswith(b"\x89PNG"))
        self.assertEqual(cl.get(ruta, headers=sesion("coord_a")).status_code, 200)
        for usuario in ("est_b", "coord_b", "doc_a1", "admin_t"):
            with self.subTest(usuario=usuario):
                self.assertEqual(cl.get(ruta, headers=sesion(usuario)).status_code, 403)
        self.assertEqual(cl.get(f"/documentos/{doc}/versiones/9/paginas/1", headers=es).status_code, 404)
        self.assertEqual(cl.get(f"/documentos/{doc}/versiones/1/paginas/99", headers=es).status_code, 404)
        self.assertEqual(cl.get("/documentos/99999/versiones/1/paginas/1", headers=es).status_code, 404)

    def test_la_cita_antigua_sigue_abriendo_su_version_tras_actualizar(self):
        es, co = sesion("est_a"), sesion("coord_a")
        v1 = pdf("Normativa de plazos VERSION UNO", "El plazo de entrega es la semana ocho del periodo.", 1)
        v2 = pdf("Normativa de plazos VERSION DOS", "El plazo de entrega cambia a la semana doce.", 1)
        subir = lambda contenido: cl.post("/documentos", data={"carrera": A}, headers=co, files={  # noqa: E731
            "archivo": ("plazos.pdf", contenido, "application/pdf")})
        self.assertEqual(subir(v1).json()["version"], 1)
        doc = bd.documento(A, None, "plazos.pdf")["id"]
        cid = cl.post("/conversaciones", data={"titulo": "plazos"}, headers=es).json()["id"]
        preguntar(es, "¿Cuál es el plazo?", conversacion_id=cid, citas=[(doc, 1, 1)])
        antes = cl.get(f"/documentos/{doc}/versiones/1/paginas/1", headers=es).content

        self.assertEqual(subir(v2).json()["version"], 2)
        # el archivo de la v1 se archivo y la ruta original ahora es la v2
        self.assertIn("_versiones", bd.version_de(doc, 1)["ruta"])
        self.assertNotIn("_versiones", bd.version_de(doc, 2)["ruta"])
        cita = cl.get(f"/conversaciones/{cid}", headers=es).json()[1]["citas"][0]
        self.assertEqual(cita["version"], 1)
        despues = cl.get(f"/documentos/{doc}/versiones/{cita['version']}/paginas/1", headers=es).content
        vigente = cl.get(f"/documentos/{doc}/versiones/2/paginas/1", headers=es).content
        self.assertEqual(despues, antes, "la cita historica debe mostrar la misma pagina de la v1")
        self.assertNotEqual(despues, vigente, "la v1 y la v2 son documentos distintos")

    def test_no_se_borra_un_documento_citado(self):
        es, co = sesion("est_a"), sesion("coord_a")
        cl.post("/documentos", data={"carrera": A}, headers=co,
                files={"archivo": ("citado.pdf", pdf("Citado", "texto de respaldo " * 10), "application/pdf")})
        d = bd.documento(A, None, "citado.pdf")
        cid = cl.post("/conversaciones", data={"titulo": "citado"}, headers=es).json()["id"]
        preguntar(es, "¿Qué dice?", conversacion_id=cid, citas=[(d["id"], 1, 1)])

        r = cl.delete(f"/documentos/{d['id']}", headers=co)
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("citan", r.json()["detail"])
        self.assertIsNotNone(bd.documento_por_id(d["id"]))
        self.assertTrue(os.path.exists(os.path.join(bd.DOCS, d["ruta"])))
        with self.assertRaises(sqlite3.IntegrityError):      # la BD tambien lo impide
            with bd.transaccion() as c:
                c.execute("DELETE FROM documento_versiones WHERE documento_id=?", (d["id"],))
        # desactivarlo si se puede, y la cita historica se sigue abriendo
        self.assertEqual(cl.patch(f"/documentos/{d['id']}/estado", json={"activo": False}, headers=co).status_code, 200)
        self.assertEqual(cl.get(f"/documentos/{d['id']}/versiones/1/paginas/1", headers=es).status_code, 200)
        # si el estudiante borra su conversacion, ya nadie lo cita y se puede eliminar
        self.assertEqual(cl.delete(f"/conversaciones/{cid}", headers=es).status_code, 200)
        self.assertEqual(cl.delete(f"/documentos/{d['id']}", headers=co).status_code, 200)
        self.assertIsNone(bd.documento_por_id(d["id"]))


# ============================== ANALITICA ==============================
class PruebasAnalitica(unittest.TestCase):
    """RF-17, RF-21 y RNF-04: agregados por categoria, sin preguntas ni usuarios."""

    SENSIBLE = ("Soy Juan Pérez, cédula 1104567890, correo juan.perez@utpl.edu.ec. "
                "¿Cuántas horas de prácticas necesito?")

    @classmethod
    def setUpClass(cls):
        # carrera y cursos propios para que los conteos no dependan de otras pruebas
        cls.carrera = "analitica"
        bd.crear_carrera(cls.carrera)
        for curso in ("Curso X", "Curso Y"):
            bd.crear_curso(cls.carrera, curso)
        for usuario, rol in (("an_est", "estudiante"), ("an_coord", "coordinacion"),
                             ("an_doc_x", "docente"), ("an_doc_y", "docente")):
            auth.crear_usuario(usuario, usuario, f"{usuario}@prueba.local", CLAVE, rol, [cls.carrera])
        bd.asignar_docentes(cls.carrera, "Curso X", ["an_doc_x"])
        bd.asignar_docentes(cls.carrera, "Curso Y", ["an_doc_y"])
        es = sesion("an_est")
        cls.conversacion = cl.post("/conversaciones", data={"titulo": "datos"}, headers=es).json()["id"]
        consultas = [  # (pregunta, curso, modo, con_respaldo) -> categoria esperada
            (cls.SENSIBLE, None, "general", True),                                   # horas
            ("¿Cuántas horas dura el prácticum?", None, "general", True),            # horas
            ("¿Cuál es el plazo para entregar?", "Curso X", "curso", False),         # plazos
            ("¿Hasta qué fecha puedo entregar?", "Curso X", "ambos", False),         # plazos
            ("¿Qué formato tiene el informe final?", "Curso Y", "curso", True),      # formatos
            ("¿Cómo se pondera la evaluación?", None, "general", True),              # evaluacion
            ("¿Dónde está la cafetería?", None, "general", False),                   # otros
        ]
        for pregunta, curso, modo, respaldo in consultas:
            r, _ = preguntar(es, pregunta, carrera=cls.carrera, curso=curso, modo=modo,
                             conversacion_id=cls.conversacion, con_respaldo=respaldo)
            assert r.status_code == 200, r.text
        cls.total = len(consultas)

    def panel(self, usuario, **params):
        return cl.get("/metricas", params={"carrera": self.carrera, **params}, headers=sesion(usuario))

    def test_agregados_por_categoria_y_brechas(self):
        d = self.panel("an_coord").json()
        self.assertEqual((d["total"], d["con_respaldo"], d["sin_respaldo"], d["pct_respaldo"]), (7, 4, 3, 57))
        self.assertEqual({c["clave"]: (c["total"], c["sin_respaldo"]) for c in d["categorias"]},
                         {"horas": (2, 0), "plazos": (2, 2), "formatos": (1, 0),
                          "evaluacion": (1, 0), "otros": (1, 1)})
        self.assertEqual([b["clave"] for b in d["brechas"]], ["plazos", "otros"])
        self.assertEqual(d["brechas"][0]["pct_sin_respaldo"], 100)
        self.assertEqual(d["ambitos"], [{"curso": None, "total": 4, "sin_respaldo": 1},
                                        {"curso": "Curso X", "total": 2, "sin_respaldo": 2},
                                        {"curso": "Curso Y", "total": 1, "sin_respaldo": 0}])
        self.assertEqual(d["sinteticas"], 0)

    def test_el_panel_no_expone_preguntas_ni_personas(self):
        crudo = self.panel("an_coord").text + self.panel("an_doc_x", curso="Curso X").text
        for dato in ("1104567890", "juan.perez", "Juan", "an_est", "cafeter", "¿"):
            with self.subTest(dato=dato):
                self.assertNotIn(dato, crudo)

    def test_la_base_no_guarda_pregunta_ni_usuario_en_la_analitica(self):
        with bd.transaccion() as c:
            columnas = [f[1] for f in c.execute("PRAGMA table_info(consulta_eventos)")]
            filas = c.execute("SELECT * FROM consulta_eventos").fetchall()
            legado = c.execute("SELECT COUNT(*) FROM consultas").fetchone()[0]
            literal = c.execute("SELECT COUNT(*) FROM mensajes WHERE texto LIKE '%1104567890%'").fetchone()[0]
        self.assertEqual(columnas, ["id", "carrera_id", "curso_id", "modo", "categoria",
                                    "con_respaldo", "origen", "dia"])
        self.assertNotIn("1104567890", json.dumps(filas))
        self.assertTrue(all(len(str(f[7])) == 10 for f in filas), "solo el dia, sin hora")
        self.assertEqual(legado, 0, "la tabla consultas (legado) ya no se escribe")
        self.assertEqual(literal, 1, "el texto solo vive en el historial del propio estudiante")

    def test_cada_rol_ve_solo_su_ambito(self):
        self.assertEqual(self.panel("an_doc_x", curso="Curso X").json()["total"], 2)
        self.assertEqual(self.panel("an_doc_x", curso="Curso X").json()["ambitos"], [])
        self.assertEqual(self.panel("an_doc_x", curso="Curso Y").status_code, 403)
        self.assertEqual(self.panel("an_doc_y", curso="Curso Y").json()["total"], 1)
        self.assertEqual(self.panel("an_coord", curso="Curso X").json()["total"], 2)
        for usuario in ("coord_a", "coord_b", "doc_a1", "an_est", "admin_t"):
            with self.subTest(usuario=usuario):
                self.assertEqual(self.panel(usuario).status_code, 403)
        # la otra carrera no ve estas consultas en su propio panel
        ajeno = cl.get("/metricas", params={"carrera": B}, headers=sesion("coord_b")).json()
        self.assertEqual(ajeno["total"], 0)

    def test_saludos_no_cuentan_y_borrar_el_historial_no_altera_los_agregados(self):
        es = sesion("an_est")
        antes = metricas.contar(self.carrera)
        r, _ = preguntar(es, "hola", carrera=self.carrera, social=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(metricas.contar(self.carrera), antes)

        cid = cl.post("/conversaciones", data={"titulo": "efimera"}, headers=es).json()["id"]
        preguntar(es, "¿Qué requisitos debo cumplir?", carrera=self.carrera, conversacion_id=cid)
        self.assertEqual(metricas.contar(self.carrera), antes + 1)
        self.assertEqual(cl.delete(f"/conversaciones/{cid}", headers=es).status_code, 200)
        with bd.transaccion() as c:
            quedan = c.execute("SELECT COUNT(*) FROM mensajes WHERE conversacion_id=?", (cid,)).fetchone()[0]
            c.execute("DELETE FROM consulta_eventos WHERE id = (SELECT MAX(id) FROM consulta_eventos)")
        self.assertEqual(quedan, 0, "los mensajes se borran con la conversacion")

    def test_vocabulario_cerrado_de_categorias(self):
        self.assertEqual(categorias.clasificar("¿Cuántas HORAS debo cumplir?"), "horas")
        self.assertEqual(categorias.clasificar("ahora mismo no sé"), "otros")
        self.assertEqual(categorias.clasificar(""), "otros")
        caid = bd.id_carrera(self.carrera)
        with self.assertRaises(sqlite3.IntegrityError):
            with bd.transaccion() as c:
                c.execute("""INSERT INTO consulta_eventos (carrera_id, modo, categoria, con_respaldo)
                             VALUES (?, 'general', 'texto libre del usuario', 1)""", (caid,))
        with bd.transaccion() as c:          # todas las claves del codigo caben en el CHECK
            for clave in categorias.CLAVES:
                c.execute("""INSERT INTO consulta_eventos (carrera_id, modo, categoria, con_respaldo, origen)
                             VALUES (?, 'general', ?, 1, 'sintetico')""", (caid, clave))
            c.execute("DELETE FROM consulta_eventos WHERE origen='sintetico' AND carrera_id=?", (caid,))


# ============================== INTEGRIDAD ==============================
class PruebasIntegridad(unittest.TestCase):
    """Relaciones entre carreras, cursos, docentes, documentos y versiones."""

    def _rechaza(self, sql, params):
        with self.assertRaises(sqlite3.IntegrityError):
            with bd.transaccion() as c:
                c.execute(sql, params)

    def test_documento_y_evento_de_un_curso_de_otra_carrera(self):
        a, curso_b = bd.id_carrera(A), bd.id_curso(B, PE)
        self._rechaza("INSERT INTO documentos (carrera_id, curso_id, nombre) VALUES (?,?,?)",
                      (a, curso_b, "cruzado.pdf"))
        self._rechaza("UPDATE documentos SET curso_id=? WHERE id=?", (curso_b, DOC["curso_p1"]))
        self._rechaza("""INSERT INTO consulta_eventos (carrera_id, curso_id, modo, categoria, con_respaldo)
                         VALUES (?,?,'curso','horas',1)""", (a, curso_b))

    def test_solo_docentes_de_la_carrera_se_asignan_a_un_curso(self):
        curso = bd.id_curso(A, P1)
        for usuario in ("doc_b", "est_a", "coord_a"):
            with self.subTest(usuario=usuario):
                self._rechaza("INSERT INTO curso_docente (curso_id, usuario_id) VALUES (?,?)",
                              (curso, bd.id_usuario(usuario)))
                with self.assertRaises(ValueError):
                    bd.asignar_docentes(A, P1, ["doc_a1", usuario])
        self.assertEqual(bd.docentes_de_curso(A, P1), ["doc_a1"])

    def test_cambiar_de_carrera_o_de_rol_retira_los_cursos(self):
        auth.crear_usuario("doc_movil", "Movil", "doc_movil@prueba.local", CLAVE, "docente", [A, B])
        bd.crear_curso(A, "Movil A")
        bd.crear_curso(B, "Movil B")
        bd.asignar_docentes(A, "Movil A", ["doc_movil"])
        bd.asignar_docentes(B, "Movil B", ["doc_movil"])
        auth.actualizar_usuario("doc_movil", carreras=[B])
        self.assertEqual(bd.cursos_de_docente("doc_movil"), [{"carrera": B, "curso": "Movil B"}])
        auth.actualizar_usuario("doc_movil", rol="estudiante")
        self.assertEqual(bd.cursos_de_docente("doc_movil"), [])

    def test_unicidad_y_claves_foraneas(self):
        self._rechaza("INSERT INTO documentos (carrera_id, curso_id, nombre) VALUES (?,NULL,?)",
                      (bd.id_carrera(A), "reglamento.pdf"))
        self._rechaza("INSERT INTO cursos (carrera_id, nombre) VALUES (?,?)", (bd.id_carrera(A), P1))
        self._rechaza("INSERT INTO documento_versiones (documento_id, numero, ruta) VALUES (?,?,?)",
                      (DOC["general_a"], 1, "otra/ruta.pdf"))
        self._rechaza("INSERT INTO cursos (carrera_id, nombre) VALUES (99999, 'huerfano')", ())
        self._rechaza("""INSERT INTO citas_mensaje (mensaje_id, documento_version_id, pagina)
                         VALUES (99999, 99999, 1)""", ())
        with bd.transaccion() as c:
            self.assertEqual(c.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(), [])
            tablas = {f[0] for f in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(len(tablas - {"sqlite_sequence"}), 17)


# ============================== MIGRACION ==============================
class PruebasMigracionV6(unittest.TestCase):
    """Una base v5 con datos pasa a v6 sin perder ni alterar filas existentes."""

    def test_migracion_v5_a_v6_aditiva_con_respaldo_y_repetible(self):
        carpeta = tempfile.mkdtemp(prefix="practicum_migracion_")
        self.addCleanup(shutil.rmtree, carpeta, ignore_errors=True)
        ruta = os.path.join(carpeta, "sistema.db")
        c = sqlite3.connect(ruta)
        with open(os.path.join(RAIZ, "pruebas", "esquema_v5.sql"), encoding="utf-8") as f:
            c.executescript(f.read())
        c.executescript("""
            INSERT INTO facultades (id, nombre) VALUES (1, '@FACULTAD@');
            INSERT INTO carreras (id, facultad_id, nombre) VALUES (1, 1, 'computacion');
            INSERT INTO cursos (id, carrera_id, nombre) VALUES (1, 1, 'Practicum 2');
            INSERT INTO roles (id, nombre) VALUES (1,'estudiante'),(2,'docente'),(3,'coordinacion'),(4,'administrador');
            INSERT INTO usuarios (id, usuario, nombre, correo, password, rol_id)
                VALUES (1, 'sintetico', 'Sintetico', 'sintetico@prueba.local', 'x$y', 1);
            INSERT INTO usuario_carrera VALUES (1, 1);
            INSERT INTO documentos (id, carrera_id, curso_id, nombre) VALUES (1, 1, NULL, 'reglamento.pdf');
            INSERT INTO documento_versiones (id, documento_id, numero, ruta, fragmentos)
                VALUES (1, 1, 1, 'computacion/global/_versiones/reglamento_v1.pdf', 5),
                       (2, 1, 2, 'computacion/global/reglamento.pdf', 6);
            INSERT INTO conversaciones (id, usuario_id, titulo) VALUES (1, 1, 'hilo');
            INSERT INTO mensajes (id, conversacion_id, rol, texto, citas) VALUES
                (1, 1, 'user', 'Mi cedula es 1100000000, cuantas horas necesito', NULL),
                (2, 1, 'bot', 'respuesta', '[{"fuente": "reglamento.pdf", "pagina": 3, "seccion": "2 Horas",
                    "documento_id": 1, "version": 1, "ref": "computacion/global/reglamento.pdf"},
                   {"fuente": "borrado.pdf", "pagina": 1, "seccion": "", "documento_id": 77, "version": 1, "ref": "x"}]');
            INSERT INTO consultas (carrera_id, curso_id, usuario_id, modo, pregunta, respondida, creado_en) VALUES
                (1, NULL, 1, 'general', 'Mi cedula es 1100000000, cuantas horas necesito', 1, '2026-10-01 10:15:00'),
                (1, 1, 1, 'ambos', 'cual es el plazo de entrega', 0, '2026-10-02 18:40:00');
        """.replace("@FACULTAD@", bd.FACULTAD_POR_DEFECTO))
        c.commit()
        antes = {t: c.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
                 for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        c.close()

        def migrar():
            entorno = {**os.environ, "PRACTICUM_DATOS": carpeta, "PYTHONIOENCODING": "utf-8"}
            return subprocess.run([sys.executable, "-c", "from nucleo import auth, parametros"],
                                  cwd=RAIZ, env=entorno, capture_output=True, text=True, timeout=120)

        r = migrar()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Respaldo previo a la migracion", r.stdout)
        respaldos = os.listdir(os.path.join(carpeta, "respaldos"))
        self.assertEqual(len(respaldos), 1)
        copia = sqlite3.connect(os.path.join(carpeta, "respaldos", respaldos[0]))
        self.assertEqual(copia.execute("PRAGMA user_version").fetchone()[0], 5)
        self.assertEqual(copia.execute("SELECT COUNT(*) FROM consultas").fetchone()[0], 2)
        copia.close()

        c = sqlite3.connect(ruta)
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 6)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(), [])
        for tabla, filas in antes.items():
            if tabla in ("parametros", "usuarios", "logs"):   # el arranque siembra parametros
                continue
            with self.subTest(tabla=tabla):
                self.assertEqual(c.execute(f"SELECT * FROM {tabla} ORDER BY 1").fetchall(), filas)
        self.assertEqual(c.execute("SELECT * FROM usuarios WHERE id=1").fetchall(), antes["usuarios"])
        # la cita apunta a la VERSION 1 (id 1), no a la vigente; la del documento borrado se omite
        self.assertEqual(c.execute("SELECT mensaje_id, documento_version_id, pagina, seccion FROM citas_mensaje").fetchall(),
                         [(2, 1, 3, "2 Horas")])
        eventos = c.execute("""SELECT carrera_id, curso_id, modo, categoria, con_respaldo, origen, dia
                               FROM consulta_eventos ORDER BY id""").fetchall()
        self.assertEqual(eventos, [(1, None, "general", "horas", 1, "migracion", "2026-10-01"),
                                   (1, 1, "ambos", "plazos", 0, "migracion", "2026-10-02")])
        self.assertNotIn("1100000000", json.dumps(c.execute("SELECT * FROM consulta_eventos").fetchall()))
        foto = [c.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in ("citas_mensaje", "consulta_eventos")]
        c.close()

        r = migrar()                               # segunda vez: ya es v6, no hace nada
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Migrando", r.stdout)
        self.assertEqual(len(os.listdir(os.path.join(carpeta, "respaldos"))), 1)
        c = sqlite3.connect(ruta)
        self.assertEqual([c.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
                          for t in ("citas_mensaje", "consulta_eventos")], foto)
        c.close()


if __name__ == "__main__":
    unittest.main()
