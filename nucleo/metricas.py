# -*- coding: utf-8 -*-
"""
REGISTRO ANONIMO de consultas.

Guarda: fecha, pregunta, si tuvo respaldo documental, y el ambito consultado.
NO se guarda quien pregunto: es un registro AGREGADO para saber que se pregunta
mas, no un log de usuarios.

Uso: la API y la app registran cada consulta con `registrar(...)` y luego
la pestana de metricas llama `resumen(...)` para pintar los agregados.
"""
import os
import sqlite3
import datetime as dt

BASE = os.path.dirname(__file__)
DB = os.path.join(os.path.dirname(BASE), "datos", "consultas.db")


def _conexion():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS consultas (
        ts TEXT,
        pregunta TEXT,
        respondida INTEGER,
        ambito TEXT
    )""")
    return c


def registrar(pregunta, con_respaldo, ambito):
    """Anota una consulta. con_respaldo True/False, ambito p.ej. 'computacion|global'."""
    c = _conexion()
    c.execute("INSERT INTO consultas VALUES (?,?,?,?)",
              (dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
               pregunta, int(bool(con_respaldo)), ambito or ""))
    c.commit()
    c.close()


def listar(prefijo=None):
    """
    Devuelve las consultas registradas (mas recientes primero).
    prefijo: por ejemplo 'computacion|' para todas las de esa carrera.
    """
    c = _conexion()
    if prefijo:
        filas = c.execute(
            "SELECT ts, pregunta, respondida, ambito FROM consultas "
            "WHERE ambito LIKE ? ORDER BY ts DESC", (prefijo + "%",)
        ).fetchall()
    else:
        filas = c.execute(
            "SELECT ts, pregunta, respondida, ambito FROM consultas ORDER BY ts DESC"
        ).fetchall()
    c.close()
    return filas


def resumen(filas):
    """Cuenta y agrupa: totales, top de preguntas, preguntas sin respaldo."""
    total = len(filas)
    con = sum(f[2] for f in filas)

    # contamos preguntas repetidas (agrupadas por texto exacto)
    conteo = {}
    for f in filas:
        conteo[f[1]] = conteo.get(f[1], 0) + 1
    top = sorted(conteo.items(), key=lambda x: -x[1])[:8]

    sin_respaldo = []
    vistos = set()
    for f in filas:
        if not f[2] and f[1] not in vistos:
            vistos.add(f[1])
            sin_respaldo.append(f[1])

    return {
        "total": total,
        "con_respaldo": con,
        "pct_respaldo": round(100 * con / total) if total else 0,
        "top": [{"pregunta": p, "n": n} for p, n in top],
        "sin_respaldo": sin_respaldo[:10],
    }
