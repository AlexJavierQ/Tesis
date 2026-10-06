# -*- coding: utf-8 -*-
"""
MODELO DE DATOS RELACIONAL (SQLite normalizado).

Esta es la FUENTE DE VERDAD de la estructura del sistema: roles, carreras,
cursos, usuarios y sesiones. Antes el rol y la carrera se guardaban como texto
suelto y los cursos se descubrian leyendo carpetas; ahora todo vive en tablas
relacionadas por claves foraneas (FK), que es un modelo mas robusto y sin
datos duplicados.

Tablas y relaciones:
  roles(id, nombre)
  carreras(id, nombre)
  cursos(id, carrera_id -> carreras, nombre)
  usuarios(id, usuario, password, rol_id -> roles, carrera_id -> carreras)
  sesiones(token, usuario_id -> usuarios, creado_en)

Los PDF siguen guardandose en carpetas (datos/docs/...), pero QUE carreras y
cursos existen lo decide esta base de datos, no el sistema de archivos.
"""
import os
import sqlite3

BASE = os.path.dirname(__file__)
DB = os.path.join(os.path.dirname(BASE), "datos", "sistema.db")
DOCS = os.path.join(os.path.dirname(BASE), "datos", "docs")

ROLES = ("estudiante", "docente", "coordinacion")
CARRERA_POR_DEFECTO = "computacion"


def conexion():
    """
    Abre una conexion a la BD relacional.
    OJO: SQLite trae las claves foraneas DESACTIVADAS por defecto (por
    compatibilidad historica). Hay que encenderlas en CADA conexion con el
    PRAGMA, si no las FK no se verifican.
    """
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("PRAGMA foreign_keys = ON")
    return c


# ---------- creacion del esquema ----------
def _crear_tablas(c):
    c.execute("""CREATE TABLE IF NOT EXISTS roles (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT UNIQUE NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS carreras (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT UNIQUE NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cursos (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        nombre      TEXT NOT NULL,
        UNIQUE (carrera_id, nombre)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id          INTEGER PRIMARY KEY,
        usuario     TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL,
        rol_id      INTEGER NOT NULL REFERENCES roles(id),
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sesiones (
        token       TEXT PRIMARY KEY,
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        creado_en   TEXT NOT NULL
    )""")


def _seed(c):
    """
    Siembra los datos iniciales y MIGRA la estructura que ya existia en disco.
    - roles: los tres fijos.
    - carreras y cursos: se descubren de las carpetas datos/docs/ existentes,
      para no perder la estructura ya creada (p. ej. el curso 'Practicum 2').
    (Los usuarios demo los siembra auth.py.)
    """
    for r in ROLES:
        c.execute("INSERT OR IGNORE INTO roles (nombre) VALUES (?)", (r,))

    c.execute("INSERT OR IGNORE INTO carreras (nombre) VALUES (?)",
              (CARRERA_POR_DEFECTO,))

    if os.path.isdir(DOCS):
        for carrera in sorted(os.listdir(DOCS)):
            cdir = os.path.join(DOCS, carrera)
            if not os.path.isdir(cdir):
                continue
            c.execute("INSERT OR IGNORE INTO carreras (nombre) VALUES (?)", (carrera,))
            cid = c.execute("SELECT id FROM carreras WHERE nombre=?", (carrera,)).fetchone()[0]
            cursos_dir = os.path.join(cdir, "cursos")
            if os.path.isdir(cursos_dir):
                for curso in sorted(os.listdir(cursos_dir)):
                    if os.path.isdir(os.path.join(cursos_dir, curso)):
                        c.execute("INSERT OR IGNORE INTO cursos (carrera_id, nombre) VALUES (?,?)",
                                  (cid, curso))
    c.commit()


def inicializar():
    c = conexion()
    _crear_tablas(c)
    _seed(c)
    c.close()


# ---------- catalogo: roles ----------
def id_rol(nombre):
    """id del rol por su nombre, o None si no existe."""
    c = conexion()
    fila = c.execute("SELECT id FROM roles WHERE nombre=?", (nombre,)).fetchone()
    c.close()
    return fila[0] if fila else None


# ---------- catalogo: carreras ----------
def carreras():
    """Nombres de todas las carreras (orden alfabetico)."""
    c = conexion()
    filas = c.execute("SELECT nombre FROM carreras ORDER BY nombre").fetchall()
    c.close()
    return [f[0] for f in filas]


def id_carrera(nombre):
    """id de la carrera por su nombre, o None si no existe."""
    c = conexion()
    fila = c.execute("SELECT id FROM carreras WHERE nombre=?", (nombre,)).fetchone()
    c.close()
    return fila[0] if fila else None


def crear_carrera(nombre):
    """Alta de una carrera. Levanta ValueError si ya existe."""
    c = conexion()
    try:
        c.execute("INSERT INTO carreras (nombre) VALUES (?)", (nombre,))
        c.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Esa carrera ya existe.")
    finally:
        c.close()


# ---------- catalogo: cursos ----------
def cursos(carrera):
    """Nombres de los cursos de una carrera (JOIN cursos-carreras)."""
    c = conexion()
    filas = c.execute("""
        SELECT cu.nombre
        FROM cursos cu
        JOIN carreras ca ON cu.carrera_id = ca.id
        WHERE ca.nombre = ?
        ORDER BY cu.nombre
    """, (carrera,)).fetchall()
    c.close()
    return [f[0] for f in filas]


def crear_curso(carrera, nombre):
    """Alta de un curso dentro de una carrera. ValueError si ya existe."""
    cid = id_carrera(carrera)
    if not cid:
        raise ValueError("Carrera no encontrada.")
    c = conexion()
    try:
        c.execute("INSERT INTO cursos (carrera_id, nombre) VALUES (?,?)", (cid, nombre))
        c.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Ese curso ya existe.")
    finally:
        c.close()


# al importar el modulo se asegura el esquema y los datos iniciales
inicializar()
