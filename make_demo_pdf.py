# -*- coding: utf-8 -*-
"""
Genera el corpus de DESARROLLO de la plataforma.

  docs/computacion/global/              -> reglamentos e instructivos (coordinacion)
  docs/computacion/cursos/Practicum 1/  -> silabo del curso (docente)
  docs/computacion/cursos/Practicum 2/  -> silabo del curso (docente)

AVISO IMPORTANTE
Estos documentos son FICTICIOS, redactados unicamente para desarrollar y
demostrar el sistema. No son normativa de la UTPL ni de ninguna institucion,
y no deben usarse como fuente para responder consultas reales de estudiantes.
Cada archivo lleva ese aviso impreso en su primera pagina.

Para la evaluacion formal del sistema (Cap. 4) hay que sustituirlos por los
reglamentos oficiales: medir la recuperacion sobre un corpus escrito por el
mismo autor de las preguntas no demuestra nada.

Uso:  python make_demo_pdf.py     (luego  python ingest.py)
"""
import os
import textwrap

import fitz

BASE = os.path.dirname(__file__)
GLOBAL = os.path.join(BASE, "datos", "docs", "computacion", "global")
C1 = os.path.join(BASE, "datos", "docs", "computacion", "cursos", "Practicum 1")
C2 = os.path.join(BASE, "datos", "docs", "computacion", "cursos", "Practicum 2")

AVISO = ("AVISO: documento ficticio, creado solo para desarrollo y demostracion "
         "del sistema. No es normativa oficial de ninguna institucion.")

MARGEN = fitz.Rect(55, 55, 545, 780)


def escribir(folder, nombre, texto, fontsize=10):
    """
    Vuelca el texto en tantas paginas como haga falta, sin partir parrafos.

    Ojo: insert_textbox ESCRIBE ademas de devolver el espacio sobrante, asi que
    no se puede usar la propia pagina para tantear si el texto cabe (quedaria
    impreso dos veces, superpuesto). Se tantea en un documento de descarte.
    """
    os.makedirs(folder, exist_ok=True)
    doc = fitz.open()
    borrador = fitz.open()

    def cabe(bloques):
        p = borrador.new_page()
        sobra = p.insert_textbox(MARGEN, "\n\n".join(bloques), fontsize=fontsize,
                                 fontname="helv", align=0)
        borrador.delete_page(-1)
        return sobra >= 0

    pendientes = [b for b in texto.split("\n\n") if b.strip()]
    while pendientes:
        acumulado = []
        while pendientes and cabe(acumulado + [pendientes[0]]):
            acumulado.append(pendientes.pop(0))
        if not acumulado:                    # un bloque solo no cabe: se fuerza
            acumulado.append(pendientes.pop(0))
        doc.new_page().insert_textbox(MARGEN, "\n\n".join(acumulado),
                                      fontsize=fontsize, fontname="helv", align=0)

    out = os.path.join(folder, nombre)
    doc.save(out)
    print(f"  creado: {os.path.relpath(out, BASE)}  ({doc.page_count} pag.)")
    doc.close()
    borrador.close()


def limpiar(texto):
    """Quita la indentacion del literal para que el PDF no herede sangrias."""
    return textwrap.dedent(texto).strip()


# ---------------------------------------------------------------- reglamentos
REGLAMENTO_PRACTICUM = limpiar(f"""
REGLAMENTO DE PRACTICAS PREPROFESIONALES
Carrera de Computacion

{AVISO}

TITULO I - DISPOSICIONES GENERALES

Articulo 1. Objeto.
El presente reglamento regula la planificacion, ejecucion, seguimiento y evaluacion
de las practicas preprofesionales de la carrera de Computacion, gestionadas a traves
de las asignaturas denominadas Practicum.

Articulo 2. Definicion.
Las practicas preprofesionales son actividades formativas que el estudiante realiza
en un entorno laboral real, orientadas a aplicar los conocimientos adquiridos en la
carrera. No constituyen una relacion laboral entre el estudiante y la organizacion
receptora.

Articulo 3. Niveles.
Las practicas se organizan en dos niveles consecutivos: Practicum 1 y Practicum 2.
Cada nivel corresponde a una asignatura con matricula y calificacion independientes.

TITULO II - HORAS Y PRERREQUISITOS

Articulo 4. Horas totales.
Las practicas preprofesionales requieren 240 horas en total, distribuidas en dos
niveles de 120 horas cada uno: Practicum 1 (120 horas) y Practicum 2 (120 horas).

Articulo 5. Jornada maxima.
El estudiante no puede dedicar mas de 20 horas semanales a las practicas, ni mas de
4 horas diarias en dias con carga academica. La jornada debe ser compatible con el
horario de clases.

Articulo 6. Prerrequisitos.
Para iniciar Practicum 1 el estudiante debe haber aprobado el quinto semestre de la
carrera. Para iniciar Practicum 2 debe haber aprobado Practicum 1. No se permite
cursar ambos niveles en el mismo periodo academico.

Articulo 7. Convalidacion por experiencia laboral.
El estudiante que acredite una relacion laboral vigente en el area de la carrera
puede solicitar la convalidacion de hasta el 50 por ciento de las horas de Practicum 2.
La solicitud se presenta a la coordinacion de Practicum adjuntando el certificado
laboral y el detalle de funciones. La convalidacion no aplica a Practicum 1.

TITULO III - CONVENIOS Y ORGANIZACIONES RECEPTORAS

Articulo 8. Organizaciones habilitadas.
Las practicas se realizan en organizaciones con convenio vigente con la universidad,
o en dependencias internas de la propia institucion. El listado de organizaciones
con convenio esta publicado en el portal de la carrera.

Articulo 9. Practicas en el exterior.
Se admiten practicas en organizaciones del exterior siempre que exista convenio
institucional previo y el estudiante gestione su propia cobertura de salud y
movilidad. La solicitud se presenta con 60 dias de anticipacion a la coordinacion
de Practicum.

Articulo 10. Cambio de organizacion.
El estudiante puede cambiar de organizacion receptora una sola vez por nivel,
siempre que no haya superado el 50 por ciento de las horas comprometidas. El cambio
requiere autorizacion escrita del docente tutor. Las horas cumplidas en la
organizacion anterior se conservan.

Articulo 11. Incumplimiento de la organizacion.
Si la organizacion receptora incumple el plan de practicas, asigna tareas ajenas al
perfil de la carrera o interrumpe la practica sin causa, el estudiante debe
notificarlo al docente tutor en un plazo de 5 dias habiles. La coordinacion de
Practicum reasigna al estudiante y las horas cumplidas se conservan integramente.

TITULO IV - CONDICIONES DEL ESTUDIANTE

Articulo 12. Remuneracion.
Las practicas preprofesionales no son remuneradas. La organizacion receptora puede,
de forma voluntaria, reconocer un estipendio o cubrir gastos de movilidad y
alimentacion, sin que ello genere relacion laboral.

Articulo 13. Cobertura de seguro.
Durante la ejecucion de las practicas el estudiante esta cubierto por el seguro
estudiantil de accidentes de la universidad, vigente mientras mantenga matricula
activa en la asignatura de Practicum. La cobertura no se extiende a las practicas
realizadas en el exterior.

Articulo 14. Asistencia e inasistencias.
El estudiante puede acumular hasta un 10 por ciento de inasistencias justificadas
sobre el total de horas del nivel. Las horas no cumplidas se recuperan antes del
cierre del periodo. Superado ese limite, el nivel se considera no aprobado.

TITULO V - SEGUIMIENTO Y ENTREGABLES

Articulo 15. Docente tutor.
Cada estudiante tiene asignado un docente tutor que aprueba el plan de practicas,
realiza el seguimiento y evalua el informe final. Las reuniones de seguimiento son
cada dos semanas.

Articulo 16. Falta de respuesta del tutor.
Si el docente tutor no responde en un plazo de 5 dias habiles, el estudiante puede
escalar el caso a la coordinacion de Practicum, que designara un tutor sustituto si
corresponde.

Articulo 17. Formatos oficiales.
Se utiliza el formato F-01 para el plan de practicas y el formato F-02 para el
informe final. Ambos formatos estan disponibles en el portal de la carrera.

Articulo 18. Plazos de entrega.
El plan de practicas (F-01) se entrega antes de iniciar las actividades. El informe
final (F-02) se entrega en un plazo maximo de 8 dias calendario despues de finalizar
la practica, a traves del entorno virtual de aprendizaje.

Articulo 19. Prorroga.
El estudiante puede solicitar una prorroga de hasta 5 dias calendario para la entrega
del informe final, por una sola vez y con causa justificada. La solicitud se presenta
al docente tutor antes del vencimiento del plazo original.

TITULO VI - EVALUACION

Articulo 20. Nota minima.
La nota minima para aprobar cada nivel de Practicum es 7 sobre 10.

Articulo 21. Reprobacion.
El estudiante que no alcance la nota minima repite el componente en el siguiente
periodo academico, con las mismas condiciones de matricula que el resto de
asignaturas de la carrera.

Articulo 22. Consultas.
Las dudas que no resuelva este reglamento se consultan con la coordinacion de
Practicum de la carrera de Computacion.
""")

REGLAMENTO_CARRERA = limpiar(f"""
REGLAMENTO DE LA CARRERA DE COMPUTACION

{AVISO}

1. DENOMINACION Y TITULO
La carrera otorga el titulo de Ingeniero en Computacion. Tiene una duracion de nueve
semestres (4.5 anos) en modalidad presencial.

2. APROBACION DE ASIGNATURAS
La nota minima para aprobar una asignatura es 7 sobre 10. La asistencia minima
exigida es del 70 por ciento de las clases.

3. MATRICULAS
El estudiante tiene hasta tres matriculas por asignatura. La tercera matricula
requiere autorizacion de la coordinacion de la carrera.

4. REQUISITOS DE TITULACION
Para graduarse, el estudiante debe aprobar todas las asignaturas de la malla,
completar las practicas preprofesionales (Practicum) y desarrollar el Trabajo de
Integracion Curricular (TIC).

5. TRABAJO DE INTEGRACION CURRICULAR (TIC)
El TIC se desarrolla en los ultimos semestres bajo la guia de un director asignado
por la carrera. Su aprobacion es requisito para la graduacion.

6. CERTIFICADOS Y TRAMITES
Los certificados de matricula, de notas y de culminacion de estudios se solicitan en
la Secretaria de la carrera. El plazo de emision es de 3 dias habiles.

7. CONTACTO
Para tramites academicos generales, el estudiante acude a la Coordinacion de la
carrera de Computacion.
""")

GUIA_ESTUDIANTE = limpiar(f"""
GUIA DEL ESTUDIANTE DE PRACTICUM
Preguntas frecuentes

{AVISO}

Esta guia resume en lenguaje sencillo lo que establece el Reglamento de Practicas
Preprofesionales. Ante cualquier discrepancia, prevalece el reglamento.

ANTES DE EMPEZAR

Cuando puedo empezar mis practicas.
Puedes iniciar Practicum 1 cuando hayas aprobado el quinto semestre. Practicum 2
requiere tener aprobado Practicum 1.

Cuantas horas tengo que hacer.
240 horas en total: 120 en Practicum 1 y 120 en Practicum 2.

Donde puedo hacerlas.
En cualquier organizacion con convenio vigente, o en una dependencia interna de la
universidad. El listado de convenios esta en el portal de la carrera.

Que hago primero.
Presentas el plan de practicas en el formato F-01 y esperas la aprobacion de tu
docente tutor. No inicies actividades antes de esa aprobacion.

DURANTE LA PRACTICA

Cuantas horas por semana puedo dedicar.
Hasta 20 horas semanales, y no mas de 4 horas al dia si ese dia tienes clases.

Me van a pagar.
No. Las practicas preprofesionales no son remuneradas. La organizacion puede
reconocer voluntariamente movilidad o alimentacion, pero eso no genera contrato.

Estoy asegurado mientras hago las practicas.
Si. Te cubre el seguro estudiantil de accidentes mientras tengas matricula activa en
la asignatura. Esa cobertura no aplica si haces las practicas en el exterior.

Puedo faltar.
Puedes acumular hasta un 10 por ciento de inasistencias justificadas, y las horas se
recuperan antes de que cierre el periodo. Si superas ese limite, el nivel se da por
no aprobado.

Puedo cambiar de empresa.
Una vez por nivel, siempre que no hayas pasado del 50 por ciento de las horas, y con
autorizacion escrita de tu tutor. Las horas ya cumplidas no se pierden.

La empresa no cumple lo acordado.
Avisa a tu docente tutor dentro de los 5 dias habiles siguientes. La coordinacion te
reasigna y conservas todas las horas cumplidas.

Mi tutor no responde.
Si pasan 5 dias habiles sin respuesta, escribe a la coordinacion de Practicum, que
puede designar un tutor sustituto.

AL TERMINAR

Cuando entrego el informe.
Tienes 8 dias calendario desde que terminas la practica. Se sube por el entorno
virtual, en el formato F-02.

Puedo pedir mas tiempo.
Si, una sola vez, hasta 5 dias calendario adicionales y con causa justificada. Debes
pedirlo a tu tutor antes de que venza el plazo original.

Con cuanto apruebo.
Con 7 sobre 10. Si no llegas, repites el componente el siguiente periodo.

CASOS ESPECIALES

Ya trabajo en el area, me sirve.
Puedes pedir convalidacion de hasta el 50 por ciento de las horas de Practicum 2,
presentando certificado laboral y detalle de funciones. Practicum 1 no se convalida.

Quiero hacer las practicas fuera del pais.
Es posible si existe convenio institucional. Debes solicitarlo con 60 dias de
anticipacion y gestionar tu propia cobertura de salud y movilidad.

Puedo hacer los dos niveles a la vez.
No. Practicum 1 y Practicum 2 se cursan en periodos academicos distintos.
""")

SILABO_1 = limpiar(f"""
SILABO - PRACTICUM 1

{AVISO}

DESCRIPCION
Practicum 1 es el primer nivel de practicas preprofesionales. El estudiante se
integra a un entorno laboral real en tareas de apoyo y aprendizaje guiado.
Comprende 120 horas.

PRERREQUISITO
Haber aprobado el quinto semestre de la carrera.

RESULTADOS DE APRENDIZAJE
Al finalizar el nivel, el estudiante es capaz de integrarse a un equipo de trabajo,
aplicar buenas practicas de documentacion tecnica y comunicar por escrito el avance
de sus actividades.

ENTREGABLES
- Plan de practicas (formato F-01) al inicio.
- Bitacora semanal de actividades.
- Informe parcial al finalizar.

EVALUACION
- Bitacora semanal: 30 por ciento
- Informe parcial: 40 por ciento
- Evaluacion del tutor empresarial: 30 por ciento

La nota minima de aprobacion es 7 sobre 10.

DOCENTE
El curso es guiado por el docente tutor de Practicum 1, quien realiza el seguimiento
cada dos semanas.
""")

SILABO_2 = limpiar(f"""
SILABO - PRACTICUM 2

{AVISO}

DESCRIPCION
Practicum 2 es el segundo nivel de practicas preprofesionales. El estudiante
desarrolla un proyecto aplicado en la organizacion receptora con mayor autonomia.
Comprende 120 horas.

PRERREQUISITO
Haber aprobado Practicum 1.

RESULTADOS DE APRENDIZAJE
Al finalizar el nivel, el estudiante es capaz de levantar requisitos con un usuario
real, disenar e implementar una solucion acotada y sustentar sus decisiones tecnicas.

ENTREGABLES
- Informe final (formato F-02).
- Presentacion del proyecto desarrollado.

EVALUACION
- Proyecto aplicado: 50 por ciento
- Informe final: 30 por ciento
- Evaluacion del tutor empresarial: 20 por ciento

La nota minima de aprobacion es 7 sobre 10.

CONVALIDACION
El estudiante con relacion laboral vigente en el area puede solicitar convalidacion
de hasta el 50 por ciento de las horas de este nivel.

DOCENTE
El curso es guiado por el docente tutor de Practicum 2.
""")


def main():
    print("Generando corpus de desarrollo (documentos ficticios)...")
    escribir(GLOBAL, "Reglamento_de_Practicum.pdf", REGLAMENTO_PRACTICUM)
    escribir(GLOBAL, "Reglamento_de_la_Carrera.pdf", REGLAMENTO_CARRERA)
    escribir(GLOBAL, "Guia_del_Estudiante_de_Practicum.pdf", GUIA_ESTUDIANTE)
    escribir(C1, "Silabo_Practicum_1.pdf", SILABO_1)
    escribir(C2, "Silabo_Practicum_2.pdf", SILABO_2)
    print("\nListo. Ahora ejecuta:  python ingest.py")
    print("Recuerda: son documentos FICTICIOS, solo para desarrollo y demostracion.")


if __name__ == "__main__":
    main()
