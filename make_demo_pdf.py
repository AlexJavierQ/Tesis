# -*- coding: utf-8 -*-
"""
Crea un PDF de demo con reglas ficticias de Practicum, para probar el MVP
sin tener todavia los reglamentos reales.  Uso:  python make_demo_pdf.py
"""
import os
import fitz

# reglamento global de la carrera de Computacion
DOCS = os.path.join(os.path.dirname(__file__), "docs", "computacion", "global")
os.makedirs(DOCS, exist_ok=True)

TEXTO = """REGLAMENTO DE PRACTICUM (DEMO) - UTPL

QUE ES EL PRACTICUM
El Practicum es el componente de practicas preprofesionales de la carrera, donde
el estudiante aplica lo aprendido en un entorno laboral real bajo la supervision
de un docente tutor. Su objetivo es desarrollar competencias profesionales antes
de graduarse. La materia trata sobre la realizacion y el seguimiento de esas
practicas.

1. HORAS REQUERIDAS
El estudiante debe completar 160 horas de practicas preprofesionales para
aprobar el componente de Practicum. Las horas se registran semanalmente.

2. PLAZOS DE ENTREGA
El informe final de practicas se entrega en un plazo maximo de 8 dias
calendario despues de finalizar la practica. La entrega es a traves del
entorno virtual.

3. FORMATOS
El estudiante debe usar el formato oficial F-01 para el plan de practicas
y el formato F-02 para el informe final. Ambos formatos estan disponibles
en el portal de la carrera.

4. TUTOR Y SEGUIMIENTO
Cada estudiante tiene un docente tutor que aprueba el plan y evalua el
informe. Las reuniones de seguimiento son cada dos semanas.

5. APROBACION
La nota minima para aprobar el Practicum es 7 sobre 10. Si el estudiante
no alcanza la nota minima, debe repetir el componente en el siguiente
periodo academico.

6. CONTACTO
Para dudas que no resuelva este reglamento, el estudiante debe escribir a
la coordinacion de Practicum de la carrera de Computacion.
"""

doc = fitz.open()
page = doc.new_page()
rect = fitz.Rect(60, 60, 535, 770)
page.insert_textbox(rect, TEXTO, fontsize=11, fontname="helv", align=0)
out = os.path.join(DOCS, "reglamento_practicum_demo.pdf")
doc.save(out)
print("Creado:", out)
