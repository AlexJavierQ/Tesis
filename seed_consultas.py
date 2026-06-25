# -*- coding: utf-8 -*-
"""
Siembra consultas de DEMOSTRACION en consultas.db para que el panel de metricas
tenga datos (temas repetidos en distintas redacciones + algunos vacios).
Uso:  python seed_consultas.py
"""
import os
import sqlite3
import datetime as dt

DB = os.path.join(os.path.dirname(__file__), "consultas.db")
GLOBAL = "computacion|global"
P1 = "computacion|curso:Practicum 1"
REG_P = "Reglamento_de_Practicum.pdf (pag. 1)"
REG_C = "Reglamento_de_la_Carrera.pdf (pag. 1)"
SIL1 = "Silabo_Practicum_1.pdf (pag. 1)"

# (pregunta, respondida, fuentes, ambito)
DATOS = [
    ("cuantas horas de practicas necesito", 1, REG_P, GLOBAL),
    ("cuantas horas debo hacer en total de practicum", 1, REG_P, GLOBAL),
    ("el total de horas de practicas cual es", 1, REG_P, GLOBAL),
    ("cual es el plazo para entregar el informe", 1, REG_P, GLOBAL),
    ("en cuantos dias entrego el informe final", 1, REG_P, GLOBAL),
    ("que formato uso para el informe final", 1, REG_P, GLOBAL),
    ("cual es la nota minima para aprobar practicum", 1, REG_P, GLOBAL),
    ("que titulo otorga la carrera de computacion", 1, REG_C, GLOBAL),
    ("donde esta el documento del TIC en la biblioteca", 0, "", GLOBAL),
    ("donde puedo conseguir el formato del TIC", 0, "", GLOBAL),
    ("cuanto cuesta la matricula", 0, "", GLOBAL),
    ("cuantas horas son en practicum 1", 1, SIL1, P1),
    ("cual es el prerrequisito de practicum 1", 1, SIL1, P1),
    ("como se evalua practicum 1", 1, SIL1, P1),
]


def main():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS consultas (ts TEXT, pregunta TEXT, respondida INTEGER, fuentes TEXT, ambito TEXT)")
    base = dt.datetime.now() - dt.timedelta(days=2)
    for i, (p, ok, fu, amb) in enumerate(DATOS):
        ts = (base + dt.timedelta(hours=i * 3)).strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO consultas VALUES (?,?,?,?,?)", (ts, p, ok, fu, amb))
    c.commit()
    n = c.execute("SELECT COUNT(*) FROM consultas").fetchone()[0]
    c.close()
    print(f"Sembradas {len(DATOS)} consultas de demo. Total en la base: {n}")


if __name__ == "__main__":
    main()
