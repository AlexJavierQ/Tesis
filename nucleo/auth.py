# -*- coding: utf-8 -*-
"""
AUTENTICACION (login).

Tres roles:
  estudiante     -> puede preguntar en el chat
  docente        -> ademas puede subir documentos de sus cursos
  coordinacion   -> ademas puede subir reglamentos generales y ver metricas

Almacenamiento: SQLite con dos tablas:
  usuarios(usuario, hash_password, rol, carrera)
  sesiones(token, usuario, creado_en)

La contrasena NUNCA se guarda en claro. Se guarda su HASH (PBKDF2-HMAC-SHA256
con sal aleatoria y 200.000 iteraciones), un estandar recomendado por NIST.
"""
import os
import sqlite3
import hashlib
import secrets
import datetime as dt

BASE = os.path.dirname(__file__)
DB = os.path.join(os.path.dirname(BASE), "datos", "usuarios.db")
ITERACIONES = 200_000   # coste del hash: alto = mas seguro y mas lento


# ---------- utilidades de hash ----------
def _hashear(password, sal=None):
    """Devuelve 'sal$hash' listo para guardar en la BD."""
    if sal is None:
        sal = secrets.token_hex(16)     # 32 caracteres hex aleatorios
    h = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), sal.encode(), ITERACIONES
    ).hex()
    return f"{sal}${h}"


def _verificar(password, guardado):
    """Compara una contrasena en claro contra el 'sal$hash' guardado."""
    try:
        sal, _ = guardado.split("$", 1)
    except ValueError:
        return False
    return _hashear(password, sal) == guardado


# ---------- inicializacion de la BD ----------
def _conexion():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        usuario TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        rol TEXT NOT NULL,
        carrera TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sesiones (
        token TEXT PRIMARY KEY,
        usuario TEXT NOT NULL,
        creado_en TEXT NOT NULL
    )""")
    return c


def _seed():
    """Crea usuarios de demostracion la primera vez, si la tabla esta vacia."""
    c = _conexion()
    n = c.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if n == 0:
        demos = [
            ("estudiante", "demo2026", "estudiante", "computacion"),
            ("docente",    "demo2026", "docente",    "computacion"),
            ("coord",      "demo2026", "coordinacion", "computacion"),
        ]
        for u, p, r, ca in demos:
            c.execute("INSERT INTO usuarios VALUES (?,?,?,?)",
                      (u, _hashear(p), r, ca))
        c.commit()
    c.close()


# ---------- API publica ----------
def crear_usuario(usuario, password, rol, carrera):
    """Alta manual de un usuario. Levanta ValueError si ya existe."""
    if rol not in ("estudiante", "docente", "coordinacion"):
        raise ValueError("Rol no valido.")
    c = _conexion()
    try:
        c.execute("INSERT INTO usuarios VALUES (?,?,?,?)",
                  (usuario, _hashear(password), rol, carrera))
        c.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Ese usuario ya existe.")
    finally:
        c.close()


def login(usuario, password):
    """
    Si las credenciales son correctas, crea una sesion y devuelve el token.
    Si no, devuelve None.
    """
    c = _conexion()
    fila = c.execute(
        "SELECT password, rol, carrera FROM usuarios WHERE usuario=?", (usuario,)
    ).fetchone()
    if not fila or not _verificar(password, fila[0]):
        c.close()
        return None
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO sesiones VALUES (?,?,?)",
              (token, usuario, dt.datetime.now().isoformat()))
    c.commit()
    c.close()
    return token


def usuario_de(token):
    """Devuelve el dict del usuario dueno del token, o None si no existe."""
    if not token:
        return None
    c = _conexion()
    fila = c.execute("""
        SELECT u.usuario, u.rol, u.carrera
        FROM sesiones s JOIN usuarios u ON s.usuario = u.usuario
        WHERE s.token = ?
    """, (token,)).fetchone()
    c.close()
    if not fila:
        return None
    return {"usuario": fila[0], "rol": fila[1], "carrera": fila[2]}


def logout(token):
    """Cierra la sesion (borra el token)."""
    c = _conexion()
    c.execute("DELETE FROM sesiones WHERE token=?", (token,))
    c.commit()
    c.close()


# al importar el modulo se aseguran los usuarios demo
_seed()
