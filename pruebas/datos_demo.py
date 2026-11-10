# -*- coding: utf-8 -*-
"""
DATOS SINTETICOS para la demostracion de la V1. SOLO USO LOCAL.

    python -m pruebas.datos_demo            # crea lo que falte (repetible)
    python -m pruebas.datos_demo --quitar   # retira lo que este script creo

Que crea (nada de esto son datos reales ni resultados de evaluacion):
  - Las cuentas de prueba de siempre (estudiante, docente, coord, admin).
  - Un segundo curso de Computacion ("Practicum 3") con otro docente
    (docente2), para mostrar que un docente no gestiona cursos ajenos.
  - Una segunda carrera ("electronica") con su coordinacion (coord2) y un
    estudiante (estudiante2), para mostrar que nadie ve carreras ajenas.
  - Eventos de analitica marcados con origen 'sintetico' (el panel avisa que
    lo son). Salen de preguntas inventadas en este archivo: la pregunta solo se
    usa para calcular su categoria y no se guarda.

Todas las cuentas usan la contrasena demo2026. No lo ejecutes en un servidor real.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import auth, bd, metricas, rag  # noqa: E402

CLAVE = "demo2026"
COMPUTACION = bd.CARRERA_POR_DEFECTO
OTRA = "electronica"
CURSO_2, CURSO_3, CURSO_OTRA = "Practicum 2", "Practicum 3", "Practicum 1"

# (usuario, nombre, rol, carreras)
CUENTAS = [
    ("docente2", "Docente Demo 2", "docente", [COMPUTACION]),
    ("coord2", "Coordinación Electrónica Demo", "coordinacion", [OTRA]),
    ("estudiante2", "Estudiante Electrónica Demo", "estudiante", [OTRA]),
]

# (pregunta inventada, carrera, curso, tuvo respaldo, cuantas veces)
CONSULTAS = [
    ("¿Cuántas horas de prácticas debo cumplir?", COMPUTACION, None, True, 9),
    ("¿Cuánto dura el prácticum 2?", COMPUTACION, CURSO_2, True, 4),
    ("¿Qué evidencias presento en entorno laboral?", COMPUTACION, None, True, 6),
    ("¿Qué formato tiene el informe final?", COMPUTACION, CURSO_2, True, 5),
    ("¿Hay plantilla para la bitácora?", COMPUTACION, CURSO_3, False, 4),
    ("¿Cómo se pondera la evaluación del prácticum?", COMPUTACION, None, True, 5),
    ("¿Hay evaluación de recuperación?", COMPUTACION, None, True, 3),
    ("¿Cuál es el plazo para entregar el informe?", COMPUTACION, CURSO_2, True, 3),
    ("¿Hasta qué fecha puedo subir las evidencias este periodo?", COMPUTACION, CURSO_3, False, 6),
    ("¿Cuándo empieza el siguiente periodo de prácticas?", COMPUTACION, None, False, 4),
    ("¿Qué requisitos necesito para matricularme en prácticum 3?", COMPUTACION, None, True, 4),
    ("¿Cómo postulo a una plaza en una empresa con convenio?", COMPUTACION, None, False, 5),
    ("¿Dónde solicito la convalidación de mis prácticas?", COMPUTACION, None, False, 3),
    ("¿Quién es mi tutor académico?", COMPUTACION, CURSO_3, False, 2),
    ("¿Dónde queda la biblioteca?", COMPUTACION, None, False, 2),
    ("¿Cuántas horas de prácticas debo cumplir?", OTRA, None, False, 3),
    ("¿Qué formato tiene el informe?", OTRA, CURSO_OTRA, False, 2),
]


def crear():
    auth.crear_cuentas_de_prueba()
    if OTRA not in bd.carreras():
        bd.crear_carrera(OTRA)
    os.makedirs(rag.carpeta_global(OTRA), exist_ok=True)
    for carrera, curso in ((COMPUTACION, CURSO_3), (OTRA, CURSO_OTRA)):
        if curso not in bd.cursos(carrera):
            bd.crear_curso(carrera, curso)
        os.makedirs(rag.carpeta_curso(carrera, curso), exist_ok=True)
    for usuario, nombre, rol, carreras in CUENTAS:
        if not bd.id_usuario(usuario):
            auth.crear_usuario(usuario, nombre, f"{usuario}@utpl.edu.ec", CLAVE, rol, carreras)
    # cada docente con SU curso: docente -> Practicum 2, docente2 -> Practicum 3
    # (se agrega al docente sin quitar a los que ya estuvieran asignados)
    for curso, docente in ((CURSO_2, "docente"), (CURSO_3, "docente2")):
        if curso in bd.cursos(COMPUTACION):
            actuales = bd.docentes_de_curso(COMPUTACION, curso)
            if docente not in actuales:
                bd.asignar_docentes(COMPUTACION, curso, actuales + [docente])
    # el docente de prueba original no debe quedar en el curso del segundo docente
    en_curso_3 = [d for d in bd.docentes_de_curso(COMPUTACION, CURSO_3) if d != "docente"]
    bd.asignar_docentes(COMPUTACION, CURSO_3, en_curso_3)

    with bd.transaccion() as c:
        ya = c.execute("SELECT COUNT(*) FROM consulta_eventos WHERE origen='sintetico'").fetchone()[0]
    if not ya:
        hoy, n = date.today(), 0
        for pregunta, carrera, curso, respaldo, veces in CONSULTAS:
            if curso and curso not in bd.cursos(carrera):
                curso = None
            for _ in range(veces):
                n += 1
                dia = hoy - timedelta(days=(n * 5) % 21)       # repartidas en tres semanas
                metricas.registrar(pregunta, respaldo, carrera, curso, "ambos" if curso else "general",
                                   origen="sintetico", dia=dia.isoformat())
        print(f"  {n} eventos sinteticos de analitica creados.")
    else:
        print(f"  Ya habia {ya} eventos sinteticos: no se agregan mas.")
    print("Datos de demostracion listos. Cuentas (contrasena demo2026):")
    print("  estudiante, docente, coord, admin   -> Computacion")
    print("  docente2                            -> Computacion, curso Practicum 3")
    print("  coord2, estudiante2                 -> Electronica (carrera sintetica)")


def quitar():
    with bd.transaccion() as c:
        n = c.execute("DELETE FROM consulta_eventos WHERE origen='sintetico'").rowcount
    print(f"  {n} eventos sinteticos retirados.")
    for usuario, *_ in CUENTAS:
        auth.borrar_usuario(usuario)
    with bd.transaccion() as c:
        # solo se retiran el curso y la carrera sinteticos si quedaron sin documentos ni consultas
        for carrera, curso in ((COMPUTACION, CURSO_3), (OTRA, CURSO_OTRA)):
            c.execute("""DELETE FROM cursos WHERE nombre=?
                         AND carrera_id = (SELECT id FROM carreras WHERE nombre=?)
                         AND id NOT IN (SELECT curso_id FROM documentos WHERE curso_id IS NOT NULL)
                         AND id NOT IN (SELECT curso_id FROM consulta_eventos WHERE curso_id IS NOT NULL)""",
                      (curso, carrera))
        c.execute("""DELETE FROM carreras WHERE nombre=?
                     AND id NOT IN (SELECT carrera_id FROM cursos)
                     AND id NOT IN (SELECT carrera_id FROM documentos)
                     AND id NOT IN (SELECT carrera_id FROM consulta_eventos)
                     AND id NOT IN (SELECT carrera_id FROM usuario_carrera)""", (OTRA,))
    for carpeta in (rag.carpeta_curso(COMPUTACION, CURSO_3), rag.carpeta_curso(OTRA, CURSO_OTRA),
                    os.path.join(bd.DOCS, OTRA, "cursos"), rag.carpeta_global(OTRA),
                    os.path.join(bd.DOCS, OTRA)):
        if os.path.isdir(carpeta) and not os.listdir(carpeta):
            os.rmdir(carpeta)
    print("Datos de demostracion retirados (las cuentas estudiante/docente/coord/admin se conservan).")


if __name__ == "__main__":
    quitar() if "--quitar" in sys.argv else crear()
