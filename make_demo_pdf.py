# -*- coding: utf-8 -*-
"""
Genera documentos de DEMOSTRACION para poblar la plataforma:
  docs/computacion/global/                 -> reglamentos (coordinacion)
  docs/computacion/cursos/Practicum 1/     -> silabo del curso (docente)
  docs/computacion/cursos/Practicum 2/     -> silabo del curso (docente)

Uso:  python make_demo_pdf.py     (luego  python ingest.py)
"""
import os
import fitz

BASE = os.path.dirname(__file__)
GLOBAL = os.path.join(BASE, "docs", "computacion", "global")
C1 = os.path.join(BASE, "docs", "computacion", "cursos", "Practicum 1")
C2 = os.path.join(BASE, "docs", "computacion", "cursos", "Practicum 2")


def escribir(folder, nombre, texto, fontsize=10.5):
    os.makedirs(folder, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(55, 55, 545, 790), texto, fontsize=fontsize, fontname="helv", align=0)
    out = os.path.join(folder, nombre)
    doc.save(out)
    print("  creado:", os.path.relpath(out, BASE))


REGLAMENTO_CARRERA = """REGLAMENTO DE LA CARRERA DE COMPUTACION (documento de demostracion)

1. DENOMINACION Y TITULO
La carrera otorga el titulo de Ingeniero en Computacion. Tiene una duracion de nueve
semestres (4.5 anos) en modalidad presencial.

2. APROBACION DE ASIGNATURAS
La nota minima para aprobar una asignatura es 7 sobre 10. La asistencia minima exigida
es del 70% de las clases.

3. MATRICULAS
El estudiante tiene hasta tres matriculas por asignatura. La tercera matricula requiere
autorizacion de la coordinacion de la carrera.

4. REQUISITOS DE TITULACION
Para graduarse, el estudiante debe aprobar todas las asignaturas de la malla, completar
las practicas preprofesionales (Practicum) y desarrollar el Trabajo de Integracion
Curricular (TIC).

5. TRABAJO DE INTEGRACION CURRICULAR (TIC)
El TIC se desarrolla en los ultimos semestres bajo la guia de un director asignado por la
carrera. Su aprobacion es requisito para la graduacion.

6. CONTACTO
Para tramites academicos generales, el estudiante acude a la Coordinacion de la carrera de
Computacion.
"""

REGLAMENTO_PRACTICUM = """REGLAMENTO DE PRACTICUM - PRACTICAS PREPROFESIONALES (documento de demostracion)

1. HORAS TOTALES
Las practicas preprofesionales requieren 240 horas en total, distribuidas en dos niveles:
Practicum 1 (120 horas) y Practicum 2 (120 horas).

2. REQUISITO PARA INICIAR
Para iniciar Practicum 1, el estudiante debe haber aprobado al menos el 60% de la malla
curricular.

3. PLAZOS DE ENTREGA
El informe final de cada practica se entrega en un plazo maximo de 8 dias calendario
despues de finalizar la practica, a traves del entorno virtual.

4. FORMATOS OFICIALES
Se usa el formato F-01 para el plan de practicas y el formato F-02 para el informe final.
Ambos formatos estan disponibles en el portal de la carrera.

5. TUTOR Y SEGUIMIENTO
Cada estudiante tiene un docente tutor que aprueba el plan y evalua el informe. Las
reuniones de seguimiento son cada dos semanas.

6. APROBACION
La nota minima para aprobar el Practicum es 7 sobre 10. Si el estudiante no alcanza la nota
minima, repite el componente en el siguiente periodo academico.

7. CONTACTO
Las dudas que no resuelva este reglamento se consultan con la coordinacion de Practicum de
la carrera de Computacion.
"""

SILABO_P1 = """SILABO - PRACTICUM 1 (documento de demostracion)

DESCRIPCION
Practicum 1 es el primer nivel de practicas preprofesionales. El estudiante se integra a un
entorno laboral real en tareas de apoyo y aprendizaje guiado. Comprende 120 horas.

PRERREQUISITO
Haber aprobado el quinto semestre de la carrera.

ENTREGABLES
- Plan de practicas (formato F-01) al inicio.
- Bitacora semanal de actividades.
- Informe parcial al finalizar.

EVALUACION
- Bitacora semanal: 30%
- Informe parcial: 40%
- Evaluacion del tutor empresarial: 30%

DOCENTE
El curso es guiado por el docente tutor de Practicum 1, quien realiza el seguimiento cada
dos semanas.
"""

SILABO_P2 = """SILABO - PRACTICUM 2 (documento de demostracion)

DESCRIPCION
Practicum 2 es el segundo nivel de practicas preprofesionales. El estudiante desarrolla un
proyecto aplicado en la empresa con mayor autonomia. Comprende 120 horas.

PRERREQUISITO
Haber aprobado Practicum 1.

ENTREGABLES
- Informe final (formato F-02).
- Presentacion del proyecto desarrollado.

EVALUACION
- Proyecto aplicado: 50%
- Informe final: 30%
- Evaluacion del tutor empresarial: 20%

DOCENTE
El curso es guiado por el docente tutor de Practicum 2.
"""

if __name__ == "__main__":
    escribir(GLOBAL, "Reglamento_de_la_Carrera.pdf", REGLAMENTO_CARRERA)
    escribir(GLOBAL, "Reglamento_de_Practicum.pdf", REGLAMENTO_PRACTICUM)
    escribir(C1, "Silabo_Practicum_1.pdf", SILABO_P1)
    escribir(C2, "Silabo_Practicum_2.pdf", SILABO_P2)
    print("Listo. Ahora corre:  python ingest.py")
