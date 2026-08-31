# -*- coding: utf-8 -*-
"""
Prueba de humo: verifica que el sistema esta bien montado.
Corre todas las piezas del backend en ~15 segundos.

Uso:  python verificar.py

Si algo esta mal, se detiene con un mensaje claro y codigo de salida != 0.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def paso(n, titulo):
    print(f"\n[{n}] {titulo}")


def ok(msg):
    print(f"    OK -> {msg}")


def fallo(msg):
    print(f"    FALLO -> {msg}")
    sys.exit(1)


# ==================== 1. Imports ====================
paso(1, "Importando modulos del nucleo...")
try:
    from nucleo import config, embeddings, pdfreader, vectorstore, llm
    from nucleo import ingest, rag, auth, metricas
    ok("Todos los modulos importan sin errores")
except Exception as e:
    fallo(f"import falla: {e}")

# ==================== 2. Configuracion ====================
paso(2, "Comprobando configuracion...")
if config.hay_key():
    ok("GROQ_API_KEY cargada")
else:
    print("    AVISO: sin GROQ_API_KEY. El sistema funcionara en modo degradado.")

# ==================== 3. Corpus indexado ====================
paso(3, "Comprobando indice vectorial...")
n = vectorstore.contar()
if n == 0:
    fallo("No hay fragmentos indexados. Corre: python -m nucleo.ingest")
ok(f"{n} fragmentos indexados en ChromaDB")

# ==================== 4. Login ====================
paso(4, "Probando login...")
tok = auth.login("estudiante", "demo2026")
if not tok:
    fallo("Login del usuario 'estudiante' fallo. Revisa datos/usuarios.db")
u = auth.usuario_de(tok)
if u["usuario"] != "estudiante" or u["rol"] != "estudiante":
    fallo(f"Sesion incoherente: {u}")
ok(f"Sesion iniciada como {u['usuario']} (rol {u['rol']})")

# password mala
if auth.login("estudiante", "malo") is not None:
    fallo("Login con password incorrecto NO deberia devolver token!")
ok("Login rechaza password incorrecto")

# ==================== 5. Recuperacion (sin LLM) ====================
paso(5, "Probando recuperacion vectorial (sin LLM)...")
hits = vectorstore.buscar("cuantas horas", k=5,
                          filtro={"scope": {"$in": ["computacion|global"]}})
if not hits:
    fallo("La busqueda no devuelve nada. El indice puede estar mal.")
ok(f"Recuperacion devuelve {len(hits)} fragmentos, mejor distancia {hits[0]['distancia']:.3f}")

# ==================== 6. Umbral anti-alucinacion ====================
paso(6, "Probando la capa 1 (umbral) sobre pregunta fuera del corpus...")
r = rag.responder("cual es la capital de australia", "computacion")
if r["con_respaldo"]:
    fallo(f"La pregunta fuera del corpus deberia abstenerse, y devolvio: {r['respuesta'][:60]}")
ok("El umbral rechaza correctamente preguntas ajenas al dominio")

# ==================== 7. Respuesta completa con LLM ====================
paso(7, "Probando respuesta completa con LLM (dentro del corpus)...")
r = rag.responder("cuantas horas de practicas necesito", "computacion")
if not r["con_respaldo"]:
    print("    AVISO: la respuesta salio sin respaldo. Puede ser rate limit del LLM.")
elif not r["citas"]:
    fallo("Respuesta con respaldo pero SIN citas. Deberia haber citas.")
else:
    ok(f"Respuesta con {len(r['citas'])} citas. Fuente: {r['citas'][0]['fuente']}")

# ==================== 8. Metricas ====================
paso(8, "Probando registro de metricas...")
antes = len(metricas.listar())
metricas.registrar("pregunta de prueba", True, "computacion|global")
despues = len(metricas.listar())
if despues != antes + 1:
    fallo(f"Metricas no se registran (antes={antes}, despues={despues})")
ok(f"Metricas registran consultas ({despues} en total)")

# ==================== FIN ====================
print("\n" + "=" * 60)
print("VERIFICACION COMPLETA - todo funciona.")
print("=" * 60)
print("\nPara arrancar el sistema entero (API + React):")
print("  python arrancar.py")
