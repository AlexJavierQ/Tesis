# -*- coding: utf-8 -*-
"""
AUTENTICACION (login, sesiones y CRUD de usuarios).

Usa el modelo relacional normalizado de nucleo/bd.py:
  usuarios(id, usuario, password, rol_id -> roles, carrera_id -> carreras)
  sesiones(token, usuario_id -> usuarios, creado_en)

Hacia afuera, las funciones siguen hablando en NOMBRES (rol="docente",
carrera="computacion"); por dentro se resuelven a los ids de las tablas
catalogo. Asi el resto del sistema no se entera de la normalizacion.

La contrasena NUNCA se guarda en claro: se guarda su HASH (PBKDF2-HMAC-SHA256
con sal aleatoria y 200.000 iteraciones), estandar recomendado por NIST.
"""
import hashlib
import secrets
import sqlite3
import datetime as dt

from nucleo import bd

ITERACIONES = 200_000   # coste del hash: alto = mas seguro y mas lento


# ---------- utilidades de hash ----------
def _hashear(password, sal=None):
    """Devuelve 'sal$hash' listo para guardar en la BD."""
    if sal is None:
        sal = secrets.token_hex(16)
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


# ---------- seed de usuarios demo ----------
def _seed():
    """Crea los usuarios de demostracion la primera vez (si no hay usuarios)."""
    c = bd.conexion()
    n = c.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    c.close()
    if n == 0:
        demos = [
            ("estudiante", "demo2026", "estudiante",   "computacion"),
            ("docente",    "demo2026", "docente",      "computacion"),
            ("coord",      "demo2026", "coordinacion", "computacion"),
        ]
        for u, p, r, ca in demos:
            crear_usuario(u, p, r, ca)


# ---------- CRUD de usuarios ----------
def crear_usuario(usuario, password, rol, carrera):
    """Alta de un usuario. ValueError si el rol/carrera no existen o si ya existe."""
    rid = bd.id_rol(rol)
    if not rid:
        raise ValueError("Rol no valido.")
    cid = bd.id_carrera(carrera)
    if not cid:
        raise ValueError("Carrera no valida.")
    c = bd.conexion()
    try:
        c.execute(
            "INSERT INTO usuarios (usuario, password, rol_id, carrera_id) VALUES (?,?,?,?)",
            (usuario, _hashear(password), rid, cid),
        )
        c.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Ese usuario ya existe.")
    finally:
        c.close()


def listar_usuarios():
    """Lista de usuarios con su rol y carrera (por nombre, via JOIN)."""
    c = bd.conexion()
    filas = c.execute("""
        SELECT u.usuario, r.nombre, ca.nombre
        FROM usuarios u
        JOIN roles r     ON u.rol_id = r.id
        JOIN carreras ca ON u.carrera_id = ca.id
        ORDER BY u.usuario
    """).fetchall()
    c.close()
    return [{"usuario": f[0], "rol": f[1], "carrera": f[2]} for f in filas]


def actualizar_usuario(usuario, rol=None, carrera=None, nuevo_password=None):
    """
    Actualiza rol, carrera y/o contrasena de un usuario.
    Cambiar la contrasena cierra todas sus sesiones activas.
    """
    c = bd.conexion()
    fila = c.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
    if not fila:
        c.close()
        raise ValueError("Usuario no encontrado.")
    uid = fila[0]

    if rol:
        rid = bd.id_rol(rol)
        if not rid:
            c.close()
            raise ValueError("Rol no valido.")
        c.execute("UPDATE usuarios SET rol_id=? WHERE id=?", (rid, uid))
    if carrera:
        cid = bd.id_carrera(carrera)
        if not cid:
            c.close()
            raise ValueError("Carrera no valida.")
        c.execute("UPDATE usuarios SET carrera_id=? WHERE id=?", (cid, uid))
    if nuevo_password:
        c.execute("UPDATE usuarios SET password=? WHERE id=?",
                  (_hashear(nuevo_password), uid))
        c.execute("DELETE FROM sesiones WHERE usuario_id=?", (uid,))
    c.commit()
    c.close()


def borrar_usuario(usuario):
    """Elimina un usuario. Sus sesiones caen solas por el ON DELETE CASCADE."""
    c = bd.conexion()
    c.execute("DELETE FROM usuarios WHERE usuario=?", (usuario,))
    c.commit()
    c.close()


# ---------- sesiones ----------
def login(usuario, password):
    """Si las credenciales son correctas, crea una sesion y devuelve el token."""
    c = bd.conexion()
    fila = c.execute(
        "SELECT id, password FROM usuarios WHERE usuario=?", (usuario,)
    ).fetchone()
    if not fila or not _verificar(password, fila[1]):
        c.close()
        return None
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO sesiones (token, usuario_id, creado_en) VALUES (?,?,?)",
              (token, fila[0], dt.datetime.now().isoformat()))
    c.commit()
    c.close()
    return token


def usuario_de(token):
    """Dado un token, devuelve {usuario, rol, carrera} o None."""
    if not token:
        return None
    c = bd.conexion()
    fila = c.execute("""
        SELECT u.usuario, r.nombre, ca.nombre
        FROM sesiones s
        JOIN usuarios u  ON s.usuario_id = u.id
        JOIN roles r     ON u.rol_id = r.id
        JOIN carreras ca ON u.carrera_id = ca.id
        WHERE s.token = ?
    """, (token,)).fetchone()
    c.close()
    if not fila:
        return None
    return {"usuario": fila[0], "rol": fila[1], "carrera": fila[2]}


def logout(token):
    """Cierra la sesion (borra el token)."""
    c = bd.conexion()
    c.execute("DELETE FROM sesiones WHERE token=?", (token,))
    c.commit()
    c.close()


# al importar el modulo se aseguran los usuarios demo
_seed()
