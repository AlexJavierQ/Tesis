"""
Dibuja documentacion/modelo_bd_sql.png a partir del esquema de nucleo/bd.py.

Cada clave foranea es una linea entre la tabla hija (lado N) y la tabla
padre (lado 1). Linea continua = relacion obligatoria (FK NOT NULL);
linea discontinua = opcional (la FK admite NULL).

Uso:  python documentacion/generar_modelo_bd.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

SALIDA = Path(__file__).with_name("modelo_bd_sql.png")

ANCHO, CABECERA, FILA, PASO = 5.5, 0.85, 0.55, 7.7

COLORES = {
    "academico": "#3d68d0",
    "acceso": "#2f7d9a",
    "documentos": "#2f9e78",
    "chat": "#7a5bc4",
    "analitica": "#6b7280",
    "bitacora": "#c8792b",
    "config": "#4b5563",
}

# nombre: (columna, y superior, grupo, [(campo, tipo, clave)])
# clave: "PK", "FK", "PK FK", "FK?" (FK que admite NULL) o ""
TABLAS = {
    "sesiones": (0, 1.0, "acceso", [
        ("token", "TEXT", "PK"), ("usuario_id", "INTEGER", "FK"),
        ("creado_en", "DATETIME", ""), ("expira_en", "DATETIME", "")]),
    "logs": (0, 5.0, "bitacora", [
        ("id", "INTEGER", "PK"), ("usuario_id", "INTEGER", "FK?"),
        ("accion", "TEXT", ""), ("detalle", "TEXT", ""), ("creado_en", "DATETIME", "")]),
    "parametros": (0, 9.6, "config", [
        ("clave", "TEXT", "PK"), ("valor", "TEXT", ""),
        ("tipo", "entero | decimal | texto", ""), ("minimo", "REAL", ""),
        ("maximo", "REAL", ""), ("descripcion", "TEXT", ""),
        ("actualizado_por", "INTEGER", "FK?"), ("actualizado_en", "DATETIME", "")]),

    "roles": (1, 0.4, "acceso", [
        ("id", "INTEGER", "PK"), ("nombre", "TEXT UNIQUE", "")]),
    "usuarios": (1, 3.0, "acceso", [
        ("id", "INTEGER", "PK"), ("usuario", "TEXT UNIQUE", ""),
        ("nombre", "TEXT", ""), ("correo", "TEXT UNIQUE", ""),
        ("password", "TEXT (hash)", ""), ("rol_id", "INTEGER", "FK"),
        ("activo", "INTEGER (0/1)", ""), ("creado_en", "DATETIME", "")]),
    "conversaciones": (1, 9.6, "chat", [
        ("id", "INTEGER", "PK"), ("usuario_id", "INTEGER", "FK"),
        ("titulo", "TEXT", ""), ("iniciada_en", "DATETIME", ""),
        ("resumen", "TEXT", ""), ("resumen_hasta", "INTEGER", "")]),
    "mensajes": (1, 15.0, "chat", [
        ("id", "INTEGER", "PK"), ("conversacion_id", "INTEGER", "FK"),
        ("rol", "user | bot", ""), ("texto", "TEXT", ""),
        ("citas", "TEXT (JSON)", ""), ("creado_en", "DATETIME", "")]),

    "usuario_carrera": (2, 2.2, "academico", [
        ("usuario_id", "INTEGER", "PK FK"), ("carrera_id", "INTEGER", "PK FK")]),
    "consultas": (2, 5.2, "analitica", [
        ("id", "INTEGER", "PK"), ("carrera_id", "INTEGER", "FK"),
        ("curso_id", "INTEGER", "FK?"), ("usuario_id", "INTEGER", "FK?"),
        ("modo", "general | curso | ambos", ""), ("pregunta", "TEXT", ""),
        ("respondida", "INTEGER (0/1)", ""), ("creado_en", "DATETIME", "")]),
    "curso_docente": (2, 11.4, "academico", [
        ("curso_id", "INTEGER", "PK FK"), ("usuario_id", "INTEGER", "PK FK")]),

    "facultades": (3, 0.4, "academico", [
        ("id", "INTEGER", "PK"), ("nombre", "TEXT UNIQUE", "")]),
    "carreras": (3, 3.4, "academico", [
        ("id", "INTEGER", "PK"), ("facultad_id", "INTEGER", "FK"),
        ("nombre", "TEXT UNIQUE", "")]),
    "cursos": (3, 7.4, "academico", [
        ("id", "INTEGER", "PK"), ("carrera_id", "INTEGER", "FK"),
        ("nombre", "TEXT", "")]),

    "documentos": (4, 4.4, "documentos", [
        ("id", "INTEGER", "PK"), ("carrera_id", "INTEGER", "FK"),
        ("curso_id", "INTEGER", "FK?"), ("nombre", "TEXT", ""),
        ("activo", "INTEGER (0/1)", ""), ("vigencia", "TEXT", ""),
        ("creado_en", "DATETIME", "")]),
    "documento_versiones": (4, 10.4, "documentos", [
        ("id", "INTEGER", "PK"), ("documento_id", "INTEGER", "FK"),
        ("numero", "INTEGER", ""), ("ruta", "TEXT UNIQUE", ""),
        ("fragmentos", "INTEGER", ""), ("subido_por", "INTEGER", "FK?"),
        ("subido_en", "DATETIME", ""), ("restaurada_de", "INTEGER", "")]),
}

# (hija, campo FK, padre, ruta)
# ruta: lista de puntos intermedios; los extremos se calculan solos.
#   "lado" de salida/llegada: "der", "izq", "arr", "aba"
#   "llegada": y (o x si el lado es arr/aba) donde la linea toca al padre
RELACIONES = [
    ("usuarios", "rol_id", "roles", dict(sale="arr", llega="aba")),
    ("sesiones", "usuario_id", "usuarios", dict(sale="der", llega="izq", en=4.125)),
    ("logs", "usuario_id", "usuarios", dict(sale="der", llega="izq", en=5.6)),
    ("parametros", "actualizado_por", "usuarios", dict(sale="der", llega="izq", en=7.1)),
    ("conversaciones", "usuario_id", "usuarios", dict(sale="arr", llega="aba")),
    ("mensajes", "conversacion_id", "conversaciones", dict(sale="arr", llega="aba")),
    ("usuario_carrera", "usuario_id", "usuarios", dict(sale="izq", llega="der", en=4.125)),
    ("consultas", "usuario_id", "usuarios", dict(sale="izq", llega="der", en=5.3)),
    ("curso_docente", "usuario_id", "usuarios", dict(sale="izq", llega="der", en=6.4)),
    ("documento_versiones", "subido_por", "usuarios",
     dict(sale="izq", llega="der", en=7.75, carril=PASO + ANCHO + 0.3)),
    ("usuario_carrera", "carrera_id", "carreras", dict(sale="der", llega="izq", en=4.3)),
    ("consultas", "carrera_id", "carreras", dict(sale="der", llega="izq", en=5.3)),
    ("consultas", "curso_id", "cursos", dict(sale="der", llega="izq", en=8.3)),
    ("curso_docente", "curso_id", "cursos", dict(sale="der", llega="izq", en=9.3)),
    ("carreras", "facultad_id", "facultades", dict(sale="arr", llega="aba")),
    ("cursos", "carrera_id", "carreras", dict(sale="arr", llega="aba")),
    ("documentos", "carrera_id", "carreras", dict(sale="izq", llega="der", en=4.9)),
    ("documentos", "curso_id", "cursos", dict(sale="izq", llega="der", en=8.3)),
    ("documento_versiones", "documento_id", "documentos", dict(sale="arr", llega="aba")),
]

TINTA, TENUE, BORDE, LINEA = "#1f2937", "#6b7280", "#cbd2dc", "#475569"


def x0(t):
    return TABLAS[t][0] * PASO


def caja(t):
    col, y, _, campos = TABLAS[t]
    return col * PASO, y, ANCHO, CABECERA + len(campos) * FILA


def y_campo(t, campo):
    _, y, _, campos = TABLAS[t]
    i = [c[0] for c in campos].index(campo)
    return y + CABECERA + i * FILA + FILA / 2


def opcional(t, campo):
    return dict((c[0], c[2]) for c in TABLAS[t][3])[campo] == "FK?"


def dibujar_tabla(ax, nombre):
    x, y, w, h = caja(nombre)
    _, _, grupo, campos = TABLAS[nombre]
    color = COLORES[grupo]
    ax.add_patch(FancyBboxPatch((x + 0.06, y + 0.08), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                                fc="#e5e9f0", ec="none", zorder=1))
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12",
                                fc="white", ec=BORDE, lw=1.2, zorder=2))
    ax.add_patch(FancyBboxPatch((x, y), w, CABECERA, boxstyle="round,pad=0,rounding_size=0.12",
                                fc=color, ec=color, zorder=3))
    ax.add_patch(plt.Rectangle((x, y + CABECERA - 0.15), w, 0.15, fc=color, ec="none", zorder=3))
    ax.text(x + w / 2, y + CABECERA / 2, nombre, ha="center", va="center",
            color="white", fontsize=12.5, fontweight="bold", zorder=4)
    for i, (campo, tipo, clave) in enumerate(campos):
        fy = y + CABECERA + i * FILA
        if i:
            ax.plot([x + 0.12, x + w - 0.12], [fy, fy], color="#e6e9ef", lw=0.8, zorder=3)
        es_pk = "PK" in clave
        ax.text(x + 0.22, fy + FILA / 2, campo, ha="left", va="center", fontsize=10.2,
                color=color if es_pk else TINTA, fontweight="bold" if clave else "normal", zorder=4)
        ax.text(x + 2.35, fy + FILA / 2, tipo, ha="left", va="center", fontsize=9.4,
                color=TENUE, zorder=4)
        if clave:
            etiqueta = clave.replace("FK?", "FK · null")
            ax.text(x + w - 0.18, fy + FILA / 2, etiqueta, ha="right", va="center",
                    fontsize=8.6, fontweight="bold", color=color if es_pk else TENUE, zorder=4)


def punto(t, lado, ref):
    """Punto del borde de la tabla t en el lado indicado."""
    x, y, w, h = caja(t)
    if lado == "izq":
        return x, ref
    if lado == "der":
        return x + w, ref
    if lado == "arr":
        return ref, y
    return ref, y + h


def dibujar_relacion(ax, hija, campo, padre, r):
    yf = y_campo(hija, campo)
    if r["sale"] in ("izq", "der"):
        a = punto(hija, r["sale"], yf)
        b = punto(padre, r["llega"], r["en"])
    else:  # vertical: centro de cada tabla
        xh, _, wh, _ = caja(hija)
        xp, _, wp, _ = caja(padre)
        xm = (max(xh, xp) + min(xh + wh, xp + wp)) / 2
        a = punto(hija, r["sale"], xm)
        b = punto(padre, r["llega"], xm)
    if "carril" in r:  # baja/sube por un carril vertical antes de llegar
        xs = [a[0], r["carril"], r["carril"], b[0]]
        ys = [a[1], a[1], b[1], b[1]]
    else:
        xs, ys = [a[0], b[0]], [a[1], b[1]]
    estilo = (0, (5, 3)) if opcional(hija, campo) else "solid"
    ax.plot(xs, ys, color=LINEA, lw=1.6, ls=estilo, zorder=1.5, solid_capstyle="round")
    for (px, py), (qx, qy), txt in ((a, (xs[1], ys[1]), "N"), (b, (xs[-2], ys[-2]), "1")):
        dx, dy = qx - px, qy - py
        n = max((dx * dx + dy * dy) ** 0.5, 1e-6)
        ux, uy = dx / n, dy / n
        # etiqueta un poco hacia afuera de la tabla y al costado de la linea
        lx, ly = px + ux * 0.38 - uy * 0.22, py + uy * 0.38 + ux * 0.22
        ax.text(lx, ly, txt, ha="center", va="center", fontsize=10, fontweight="bold",
                color="#1d4ed8", zorder=5,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))


def main():
    ancho_total = 4 * PASO + ANCHO
    alto_total = 22.6
    fig = plt.figure(figsize=(ancho_total * 0.62, alto_total * 0.62), dpi=130)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-0.6, ancho_total + 0.6)
    ax.set_ylim(alto_total - 0.6, -1.6)
    ax.axis("off")

    ax.text(ancho_total / 2, -0.9, "Modelo de datos · Asistente de Prácticum  (SQLite, 15 tablas, 19 claves foráneas)",
            ha="center", va="center", fontsize=17, fontweight="bold", color=TINTA)

    for hija, campo, padre, r in RELACIONES:
        dibujar_relacion(ax, hija, campo, padre, r)
    for t in TABLAS:
        dibujar_tabla(ax, t)

    # leyenda
    ly = 20.2
    grupos = [("academico", "estructura académica"), ("acceso", "usuarios y acceso"),
              ("documentos", "documentos y versiones"), ("chat", "historial de chat"),
              ("analitica", "consultas (analítica)"), ("bitacora", "bitácora"),
              ("config", "configuración")]
    x = 0
    for g, txt in grupos:
        ax.add_patch(FancyBboxPatch((x, ly - 0.22), 0.44, 0.44, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc=COLORES[g], ec="none"))
        ax.text(x + 0.62, ly, txt, va="center", fontsize=10.5, color=TINTA)
        x += ancho_total / 7
    ax.plot([0, 1.4], [ly + 1.0, ly + 1.0], color=LINEA, lw=1.6)
    ax.text(1.6, ly + 1.0, "obligatoria (FK NOT NULL)", va="center", fontsize=10, color=TINTA)
    ax.plot([7.0, 8.4], [ly + 1.0, ly + 1.0], color=LINEA, lw=1.6, ls=(0, (5, 3)))
    ax.text(8.6, ly + 1.0, "opcional (FK admite NULL)", va="center", fontsize=10, color=TINTA)
    ax.text(14.6, ly + 1.0, "1 ── N : un registro del lado 1 se relaciona con muchos del lado N.\n"
            "PK = clave primaria · FK = clave foránea · todas las fechas son DATETIME validadas con CHECK.",
            va="center", fontsize=10, color=TENUE)

    fig.savefig(SALIDA, facecolor="white")
    print("guardado", SALIDA)


if __name__ == "__main__":
    main()
