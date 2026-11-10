# -*- coding: utf-8 -*-
"""
ANALITICA DE CONSULTAS con datos minimizados.

Cada consulta del chat deja UN evento en la tabla `consulta_eventos`
(nucleo/bd.py):
  consulta_eventos(id, carrera_id -> carreras, curso_id -> cursos, modo,
                   categoria, con_respaldo, origen, dia)

Que NO se guarda: la pregunta literal, quien pregunto, la hora exacta ni la
conversacion. La pregunta solo se usa, en memoria, para calcular su categoria
(vocabulario cerrado de nucleo/categorias.py) y se descarta.

El panel muestra unicamente AGREGADOS: totales, categorias mas consultadas y
brechas documentales (categorias con consultas que quedaron sin respaldo).

La tabla `consultas` de la v5 (pregunta literal + usuario) ya no se escribe
ni se lee desde aqui.

Uso: la API registra cada consulta con `registrar(...)` y el panel de
metricas llama `resumen(carrera, curso)`.
"""
from nucleo import bd, categorias


def registrar(pregunta, con_respaldo, carrera, curso=None, modo="general",
              origen="chat", dia=None):
    """
    Anota el evento de una consulta y devuelve su id. `pregunta` solo sirve
    para clasificarla: no se almacena. Si la carrera no existe, no se registra
    (no rompe el chat) y devuelve None.
    `dia` (AAAA-MM-DD) solo lo usan los datos sinteticos; por defecto es hoy.
    """
    caid = bd.id_carrera(carrera)
    if not caid:
        return None
    cuid = bd.id_curso(carrera, curso) if curso else None
    categoria = categorias.clasificar(pregunta)
    with bd.transaccion() as c:
        return c.execute("""INSERT INTO consulta_eventos
                     (carrera_id, curso_id, modo, categoria, con_respaldo, origen, dia)
                     VALUES (?,?,?,?,?,?, IFNULL(date(?), date('now','localtime')))""",
                  (caid, cuid, modo, categoria, int(bool(con_respaldo)), origen, dia)).lastrowid


def _filtro(carrera, curso):
    """WHERE y parametros para un ambito: toda la carrera, o solo un curso."""
    sql, params = "WHERE ca.nombre = ?", [carrera]
    if curso:
        sql += " AND cu.nombre = ?"
        params.append(curso)
    return sql, params


_DESDE = """FROM consulta_eventos e
            JOIN carreras ca    ON e.carrera_id = ca.id
            LEFT JOIN cursos cu ON e.curso_id = cu.id """


def resumen(carrera, curso=None):
    """
    Agregados de un ambito (una carrera completa, o uno de sus cursos):
      total, con_respaldo, sin_respaldo, pct_respaldo
      categorias: [{clave, etiqueta, total, sin_respaldo, pct_sin_respaldo}]
                  de la mas consultada a la menos (solo las que tienen consultas)
      brechas:    las mismas categorias, pero solo las que tienen consultas SIN
                  respaldo, ordenadas por cuantas quedaron sin responder
      ambitos:    [{curso (None = normativa general), total, sin_respaldo}]
                  (solo al ver la carrera completa)
      sinteticas: cuantos eventos son datos de demostracion
      desde, hasta: primer y ultimo dia con consultas
    Nunca devuelve preguntas ni usuarios: la tabla no los tiene.
    """
    donde, params = _filtro(carrera, curso)
    with bd.transaccion() as c:
        total, con, sinteticas, desde, hasta = c.execute(f"""
            SELECT COUNT(*), IFNULL(SUM(e.con_respaldo), 0),
                   IFNULL(SUM(e.origen = 'sintetico'), 0), MIN(e.dia), MAX(e.dia)
            {_DESDE} {donde}""", params).fetchone()
        por_categoria = c.execute(f"""
            SELECT e.categoria, COUNT(*), SUM(1 - e.con_respaldo)
            {_DESDE} {donde}
            GROUP BY e.categoria ORDER BY COUNT(*) DESC, e.categoria""", params).fetchall()
        por_ambito = [] if curso else c.execute(f"""
            SELECT cu.nombre, COUNT(*), SUM(1 - e.con_respaldo)
            {_DESDE} {donde}
            GROUP BY cu.nombre ORDER BY cu.nombre IS NOT NULL, cu.nombre""", params).fetchall()

    cats = [{"clave": clave, "etiqueta": categorias.etiqueta(clave), "total": n,
             "sin_respaldo": sin, "pct_sin_respaldo": round(100 * sin / n)}
            for clave, n, sin in por_categoria]
    brechas = sorted((x for x in cats if x["sin_respaldo"]),
                     key=lambda x: (-x["sin_respaldo"], -x["pct_sin_respaldo"], x["clave"]))
    return {
        "total": total,
        "con_respaldo": con,
        "sin_respaldo": total - con,
        "pct_respaldo": round(100 * con / total) if total else 0,
        "categorias": cats,
        "brechas": brechas,
        "ambitos": [{"curso": nombre, "total": n, "sin_respaldo": sin}
                    for nombre, n, sin in por_ambito],
        "sinteticas": sinteticas,
        "desde": desde,
        "hasta": hasta,
    }


def contar(carrera=None):
    """Cuantos eventos hay (de una carrera, o de todas). Lo usan las pruebas."""
    with bd.transaccion() as c:
        if carrera:
            return c.execute(f"SELECT COUNT(*) {_DESDE} WHERE ca.nombre = ?", (carrera,)).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM consulta_eventos").fetchone()[0]
