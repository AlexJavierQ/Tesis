# -*- coding: utf-8 -*-
"""
REGISTRO DE CONSULTAS y metricas agregadas.

Las consultas viven en la tabla `consultas` de la BD principal (nucleo/bd.py),
RELACIONADA con el resto del modelo:
  consultas(id, carrera_id -> carreras, curso_id -> cursos,
            usuario_id -> usuarios (NULL si pregunto alguien sin sesion),
            modo, pregunta, respondida, creado_en)

Las METRICAS que se muestran son siempre AGREGADAS (totales, temas, vacios):
el panel nunca muestra quien pregunto que.

Uso: la API registra cada consulta con `registrar(...)` y la pestana de
metricas llama `resumen(listar(...))`.
"""
from nucleo import bd


def registrar(pregunta, con_respaldo, carrera, curso=None, modo="general", usuario=None):
    """Anota una consulta. Si la carrera no existe, no se registra (no rompe el chat)."""
    caid = bd.id_carrera(carrera)
    if not caid:
        return
    cuid = bd.id_curso(carrera, curso) if curso else None
    uid = bd.id_usuario(usuario) if usuario else None
    with bd.transaccion() as c:
        c.execute("""INSERT INTO consultas
                     (carrera_id, curso_id, usuario_id, modo, pregunta, respondida)
                     VALUES (?,?,?,?,?,?)""",
                  (caid, cuid, uid, modo, pregunta, int(bool(con_respaldo))))


def listar(carrera=None, curso=None):
    """
    Consultas registradas (mas recientes primero) como (fecha, pregunta, respondida).
    Sin filtros: todas. Con carrera: las de esa carrera. Con curso: las de ese curso.
    """
    sql = """SELECT co.creado_en, co.pregunta, co.respondida
             FROM consultas co
             JOIN carreras ca ON co.carrera_id = ca.id
             LEFT JOIN cursos cu ON co.curso_id = cu.id
             WHERE 1=1"""
    params = []
    if carrera:
        sql += " AND ca.nombre = ?"
        params.append(carrera)
    if curso:
        sql += " AND cu.nombre = ?"
        params.append(curso)
    with bd.transaccion() as c:
        return c.execute(sql + " ORDER BY co.id DESC", params).fetchall()


# similitud minima (coseno) para considerar que dos preguntas son el MISMO tema.
# Calibrado sobre consultas reales: 0.70 agrupa sinonimos claros ("cuantas horas
# necesito" ~ "cual es el total de horas" = 0.73) sin mezclar temas distintos
# ("formato del informe" vs "biblioteca" = 0.35). Subirlo pierde sinonimos;
# bajarlo mucho empieza a juntar preguntas no relacionadas.
UMBRAL_TEMA = 0.70


def agrupar_por_significado(preguntas):
    """
    Agrupa las preguntas por SIGNIFICADO, no por texto exacto.

    Ejemplo: "cuantas horas necesito" y "cual es el total de horas" se escriben
    distinto pero significan lo mismo, asi que cuentan como UN solo tema.

    Como lo hace (algoritmo simple, tipo "bola de nieve"):
      1. Convierte cada pregunta en un vector con el modelo de embeddings.
      2. Recorre las preguntas una por una. Para cada una:
         - si se parece (similitud >= UMBRAL_TEMA) a ALGUNA pregunta de un grupo
           que ya existe, la mete en ese grupo;
         - si no se parece a ninguna, abre un grupo nuevo con ella.
      3. El "tema" de cada grupo es su pregunta mas frecuente.

    Devuelve una lista de {tema, n, variantes} ordenada por n (mas preguntado
    primero), donde:
      tema      = la pregunta representante del grupo
      n         = cuantas consultas cayeron en ese tema (sumando variantes)
      variantes = cuantas formas distintas de escribirlo se agruparon
    """
    import numpy as np
    from nucleo import embeddings

    # cuenta cuantas veces se hizo cada pregunta (por texto exacto)
    conteo = {}
    for p in preguntas:
        p = (p or "").strip()
        if p:
            conteo[p] = conteo.get(p, 0) + 1
    unicas = list(conteo.keys())
    if not unicas:
        return []

    # un vector por pregunta unica (ya vienen normalizados -> np.dot = coseno)
    vecs = embeddings.embed(unicas)

    grupos = []  # cada grupo: {"miembros": [idx], "n": total_consultas}
    for i in range(len(unicas)):
        encontrado = None
        for g in grupos:
            # se une al grupo si se parece a ALGUNA pregunta que ya esta dentro
            if any(float(np.dot(vecs[i], vecs[m])) >= UMBRAL_TEMA for m in g["miembros"]):
                encontrado = g
                break
        if encontrado:
            encontrado["miembros"].append(i)
            encontrado["n"] += conteo[unicas[i]]
        else:
            grupos.append({"miembros": [i], "n": conteo[unicas[i]]})

    # el tema de cada grupo es la pregunta mas frecuente dentro del grupo
    salida = []
    for g in grupos:
        rep = max(g["miembros"], key=lambda idx: conteo[unicas[idx]])
        salida.append({
            "pregunta": unicas[rep],
            "n": g["n"],
            "variantes": len(g["miembros"]),
        })
    return sorted(salida, key=lambda x: -x["n"])


def resumen(filas):
    """Cuenta y agrupa: totales, temas mas consultados, preguntas sin respaldo."""
    total = len(filas)
    con = sum(f[2] for f in filas)

    # temas mas consultados, agrupando por SIGNIFICADO (no por texto exacto)
    top = agrupar_por_significado([f[1] for f in filas])[:8]

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
        "top": top,
        "sin_respaldo": sin_respaldo[:10],
    }
