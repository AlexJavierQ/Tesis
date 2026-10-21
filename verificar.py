# -*- coding: utf-8 -*-
"""
Prueba de humo: verifica que el sistema esta bien montado sobre el corpus oficial.

Uso:  python verificar.py

No depende de cuentas de prueba: crea un usuario temporal y lo borra al final.
Tampoco deja rastros en las metricas. Si algo esta mal, se detiene con un
mensaje claro y codigo de salida distinto de 0.
"""
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def paso(n, titulo):
    print(f"\n[{n}] {titulo}")


def ok(msg):
    print(f"    OK -> {msg}")


def aviso(msg):
    print(f"    AVISO -> {msg}")


def fallo(msg):
    print(f"    FALLO -> {msg}")
    sys.exit(1)


# ==================== 1. Imports ====================
paso(1, "Importando modulos del nucleo...")
try:
    from nucleo import config, vectorstore, ingest, rag, auth, metricas, bd, busqueda
    ok("Todos los modulos importan sin errores")
except Exception as e:
    fallo(f"import falla: {e}")

# ==================== 2. Configuracion ====================
paso(2, "Comprobando configuracion...")
if config.hay_key():
    ok("GROQ_API_KEY cargada")
else:
    aviso("sin GROQ_API_KEY: el sistema responde en modo degradado (muestra fragmentos).")

# ==================== 3. Modelo relacional ====================
paso(3, "Comprobando el modelo relacional...")
with bd.transaccion() as c:
    tablas = {f[0] for f in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    huerfanas = c.execute("PRAGMA foreign_key_check").fetchall()
esperadas = {"facultades", "carreras", "cursos", "curso_docente", "roles", "usuarios",
             "usuario_carrera", "sesiones", "documentos", "documento_versiones",
             "conversaciones", "mensajes", "consultas", "logs", "parametros"}
if esperadas - tablas:
    fallo(f"Faltan tablas: {esperadas - tablas}")
if huerfanas:
    fallo(f"Hay filas que apuntan a registros inexistentes: {huerfanas[:3]}")
ok(f"{len(esperadas)} tablas y claves foraneas integras")

# ==================== 4. Catalogo y base vectorial coherentes ====================
paso(4, "Comprobando que el catalogo y ChromaDB coincidan...")
documentos = bd.todos_los_documentos()
if not documentos:
    fallo("El catalogo de documentos esta vacio. Corre: python -m nucleo.ingest")
informe = ingest.reconciliar()
if informe["archivos_faltantes"]:
    fallo(f"Faltan archivos de documentos: {informe['archivos_faltantes']}")
if informe["reindexados"] or informe["huerfanos"] or informe["limpiados"]:
    aviso(f"se corrigieron diferencias: {informe}")
activos = [d for d in documentos if d["activo"]]
ok(f"{len(activos)} documentos activos, {vectorstore.contar()} fragmentos, sin diferencias pendientes")

# ==================== 5. Autenticacion ====================
paso(5, "Probando login con un usuario temporal...")
usuario = "verificacion_" + secrets.token_hex(3)
clave = secrets.token_urlsafe(12)
auth.crear_usuario(usuario, "Verificacion", f"{usuario}@verificacion.local", clave,
                   "estudiante", [bd.CARRERA_POR_DEFECTO])
try:
    tok = auth.login(usuario, clave)
    if not tok or auth.usuario_de(tok)["usuario"] != usuario:
        fallo("El login con la contrasena correcta no funciono.")
    if auth.login(usuario, "incorrecta") is not None:
        fallo("El login con contrasena incorrecta NO deberia funcionar.")
    ok("Login correcto acepta y login incorrecto rechaza")
finally:
    auth.borrar_usuario(usuario)

# ==================== 6. Busqueda hibrida ====================
paso(6, "Probando la busqueda hibrida (vectores + palabras clave)...")
hits = busqueda.buscar("evidencias de las practicas de insercion al entorno laboral",
                       "computacion|global", 8)
if not any("14.2" in h["meta"].get("seccion", "") for h in hits):
    fallo("La seccion 14.2 (evidencias de insercion) no aparece entre los resultados.")
ok(f"{len(hits)} secciones recuperadas, incluida la 14.2 de la Resolucion")

# ==================== 7. Abstencion fuera del dominio ====================
paso(7, "Probando el umbral anti-alucinacion con una pregunta ajena...")
r = rag.responder("cual es la capital de australia", "computacion")
if r["con_respaldo"]:
    fallo(f"Deberia abstenerse y respondio: {r['respuesta'][:60]}")
ok("Se abstiene ante preguntas ajenas a los documentos")

# ==================== 8. Respuesta completa ====================
paso(8, "Probando una respuesta completa con el modelo de lenguaje...")
r = rag.responder("¿El practicum tiene evaluacion de recuperacion?", "computacion")
if r.get("degradado"):
    aviso("el modelo no respondio (sin key o limite de Groq): se mostraron fragmentos.")
elif not r["con_respaldo"] or not r["citas"]:
    fallo(f"Respuesta sin respaldo o sin citas: {r['respuesta'][:80]}")
elif r["citas"][0]["pagina"] != 24:
    aviso(f"la primera cita es la pag. {r['citas'][0]['pagina']}; se esperaba la 24 (seccion 13.2)")
else:
    ok(f"Respuesta con respaldo; primera cita: {r['citas'][0]['fuente']}, pag. 24, version {r['citas'][0]['version']}")

# ==================== 9. Metricas ====================
paso(9, "Probando el registro de metricas (sin dejar rastro)...")
antes = len(metricas.listar())
metricas.registrar("verificacion automatica", True, bd.CARRERA_POR_DEFECTO)
despues = len(metricas.listar())
with bd.transaccion() as c:
    c.execute("DELETE FROM consultas WHERE pregunta = 'verificacion automatica'")
if despues != antes + 1:
    fallo(f"Las metricas no se registran (antes={antes}, despues={despues})")
ok("Las consultas se registran correctamente")

# ==================== FIN ====================
print("\n" + "=" * 60)
print("VERIFICACION COMPLETA - todo funciona.")
print("=" * 60)
print("\nPara arrancar el sistema entero (API + React):")
print("  python arrancar.py")
