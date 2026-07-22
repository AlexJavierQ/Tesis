# -*- coding: utf-8 -*-
"""
Registro anonimo de consultas y agregacion de metricas.

Antes esta logica estaba duplicada en app.py y api.py con esquemas de tabla
DISTINTOS (5 columnas vs 4), y por eso /preguntar reventaba con
"table consultas has 5 columns but 4 values were supplied".
Ahora hay un solo esquema y un solo lugar donde se escribe.

Privacidad: se guarda el TEXTO de la consulta y la fecha. Nunca quien pregunto.
"""
import os
import sqlite3
import datetime as dt
from collections import Counter

import numpy as np

BASE = os.path.dirname(__file__)
DB = os.path.join(os.path.dirname(BASE), "datos", "consultas.db")
COLUMNAS = ("ts", "pregunta", "respondida", "fuentes", "ambito")


def _conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("CREATE TABLE IF NOT EXISTS consultas "
              "(ts TEXT, pregunta TEXT, respondida INTEGER, fuentes TEXT, ambito TEXT)")
    # migracion suave para bases creadas por versiones anteriores
    cols = [r[1] for r in c.execute("PRAGMA table_info(consultas)").fetchall()]
    if "ambito" not in cols:
        c.execute("ALTER TABLE consultas ADD COLUMN ambito TEXT")
    return c


def registrar(pregunta, con_respaldo, fuentes, ambito):
    """Inserta una consulta. fuentes: lista[str]. ambito: el scope consultado."""
    c = _conn()
    c.execute("INSERT INTO consultas (ts, pregunta, respondida, fuentes, ambito) VALUES (?,?,?,?,?)",
              (dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
               pregunta, int(bool(con_respaldo)), " | ".join(fuentes or []), ambito or ""))
    c.commit()
    c.close()


def listar(prefix=None, exact=None):
    """Filas (ts, pregunta, respondida, ambito) filtradas por ambito."""
    c = _conn()
    if exact:
        q = "SELECT ts,pregunta,respondida,ambito FROM consultas WHERE ambito=? ORDER BY ts DESC"
        filas = c.execute(q, (exact,)).fetchall()
    elif prefix:
        q = "SELECT ts,pregunta,respondida,ambito FROM consultas WHERE ambito LIKE ? ORDER BY ts DESC"
        filas = c.execute(q, (prefix + "%",)).fetchall()
    else:
        filas = c.execute("SELECT ts,pregunta,respondida,ambito FROM consultas ORDER BY ts DESC").fetchall()
    c.close()
    return filas


def agrupar_temas(preguntas, umbral=0.68):
    """
    Agrupa preguntas por SIGNIFICADO, no por texto exacto: '¿cuantas horas?' y
    '¿el total de horas cual es?' cuentan como un mismo tema.
    Usa el mismo modelo de embeddings que la recuperacion.
    """
    from nucleo import embeddings as emb

    cnt = Counter(p.strip() for p in preguntas if p and p.strip())
    unicas = list(cnt)
    if not unicas:
        return []
    vecs = emb.embed(unicas)                       # ya vienen normalizados
    clusters = []
    for i in range(len(unicas)):
        mejor, sim_max = None, -1.0
        for cl in clusters:
            sim = float(np.dot(vecs[i], vecs[cl["rep"]]))
            if sim > sim_max:
                sim_max, mejor = sim, cl
        if mejor and sim_max >= umbral:
            mejor["miembros"].append(i)
            mejor["n"] += cnt[unicas[i]]
        else:
            clusters.append({"rep": i, "miembros": [i], "n": cnt[unicas[i]]})
    out = []
    for cl in clusters:
        rep = max(cl["miembros"], key=lambda idx: cnt[unicas[idx]])
        out.append({"tema": unicas[rep], "n": cl["n"], "variantes": len(cl["miembros"])})
    return sorted(out, key=lambda x: -x["n"])


def resumen(filas):
    """Agregado listo para pintar: totales, temas y brechas documentales."""
    total = len(filas)
    con = sum(f[2] for f in filas)
    sin_respaldo = list(dict.fromkeys(f[1] for f in filas if not f[2]))
    return {
        "total": total,
        "con_respaldo": con,
        "pct_respaldo": round(100 * con / total) if total else 0,
        "temas": agrupar_temas([f[1] for f in filas])[:8],
        "sin_respaldo": sin_respaldo[:20],
        "consultas": [{"ts": f[0], "pregunta": f[1], "respondida": bool(f[2])} for f in filas[:200]],
    }
