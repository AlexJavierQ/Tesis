# -*- coding: utf-8 -*-
"""
AUTENTICACION (login, sesiones y CRUD de usuarios).

Usa el modelo relacional de nucleo/bd.py:
  usuarios(id, usuario, nombre, correo, password, rol_id -> roles, activo, creado_en)
  usuario_carrera(usuario_id, carrera_id)        <- un usuario, muchas carreras
  sesiones(token, usuario_id, creado_en, expira_en)

Hacia afuera, las funciones hablan en NOMBRES (rol="docente",
carreras=["computacion"]); por dentro se resuelven a los ids de las tablas.

La contrasena NUNCA se guarda en claro: se guarda su HASH (PBKDF2-HMAC-SHA256
con sal aleatoria y 200.000 iteraciones), estandar recomendado por NIST.
"""
import re
import hashlib
import secrets
import sqlite3

from nucleo import bd

ITERACIONES = 200_000   # coste del hash: alto = mas seguro y mas lento
HORAS_SESION = 8        # una sesion caduca a las 8 horas
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    return secrets.compare_digest(_hashear(password, sal), guardado)


# ---------- validaciones ----------
def _validar_correo(correo):
    correo = (correo or "").strip().lower()
    if not PATRON_CORREO.match(correo):
        raise ValueError("Correo no valido.")
    return correo


def _ids_carreras(c, carreras):
    """Convierte nombres de carrera en ids. Exige al menos una y que todas existan."""
    if not carreras:
        raise ValueError("El usuario debe tener al menos una carrera.")
    ids = []
    for nombre in carreras:
        fila = c.execute("SELECT id FROM carreras WHERE nombre=?", (nombre,)).fetchone()
        if not fila:
            raise ValueError(f"Carrera no valida: {nombre}")
        ids.append(fila[0])
    return ids


# ---------- seed de usuarios demo ----------
def _seed():
    """Crea los usuarios de demostracion la primera vez (si no hay usuarios)."""
    with bd.transaccion() as c:
        n = c.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if n == 0:
        demos = [
            ("estudiante", "Estudiante Demo",   "estudiante@utpl.edu.ec", "estudiante"),
            ("docente",    "Docente Demo",      "docente@utpl.edu.ec",    "docente"),
            ("coord",      "Coordinación Demo", "coord@utpl.edu.ec",      "coordinacion"),
        ]
        for u, nombre, correo, rol in demos:
            crear_usuario(u, nombre, correo, "demo2026", rol, [bd.CARRERA_POR_DEFECTO])


# ---------- CRUD de usuarios ----------
def crear_usuario(usuario, nombre, correo, password, rol, carreras):
    """Alta de un usuario con una o varias carreras. ValueError si algo no es valido."""
    correo = _validar_correo(correo)
    try:
        with bd.transaccion() as c:
            rid = c.execute("SELECT id FROM roles WHERE nombre=?", (rol,)).fetchone()
            if not rid:
                raise ValueError("Rol no valido.")
            ids = _ids_carreras(c, carreras)
            uid = c.execute(
                "INSERT INTO usuarios (usuario, nombre, correo, password, rol_id) VALUES (?,?,?,?,?)",
                (usuario, nombre.strip() or usuario, correo, _hashear(password), rid[0]),
            ).lastrowid
            c.executemany("INSERT INTO usuario_carrera (usuario_id, carrera_id) VALUES (?,?)",
                          [(uid, cid) for cid in ids])
    except sqlite3.IntegrityError:
        raise ValueError("Ese usuario o correo ya existe.")


def _carreras_de(c, uid):
    return [f[0] for f in c.execute("""
        SELECT ca.nombre FROM usuario_carrera uc JOIN carreras ca ON uc.carrera_id = ca.id
        WHERE uc.usuario_id=? ORDER BY ca.nombre""", (uid,))]


def listar_usuarios():
    """Usuarios con su rol, correo y carreras (sin passwords)."""
    with bd.transaccion() as c:
        filas = c.execute("""
            SELECT u.id, u.usuario, u.nombre, u.correo, r.nombre, u.activo, u.creado_en
            FROM usuarios u JOIN roles r ON u.rol_id = r.id
            ORDER BY u.usuario""").fetchall()
        return [{"usuario": f[1], "nombre": f[2], "correo": f[3], "rol": f[4],
                 "activo": bool(f[5]), "creado_en": f[6], "carreras": _carreras_de(c, f[0])}
                for f in filas]


def actualizar_usuario(usuario, rol=None, carreras=None, nuevo_password=None,
                       activo=None, nombre=None, correo=None):
    """
    Actualiza los datos de un usuario (solo los campos que vienen).
    Cambiar la contrasena o desactivar al usuario cierra sus sesiones.
    """
    try:
        with bd.transaccion() as c:
            fila = c.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
            if not fila:
                raise ValueError("Usuario no encontrado.")
            uid = fila[0]
            if rol:
                rid = c.execute("SELECT id FROM roles WHERE nombre=?", (rol,)).fetchone()
                if not rid:
                    raise ValueError("Rol no valido.")
                c.execute("UPDATE usuarios SET rol_id=? WHERE id=?", (rid[0], uid))
            if carreras is not None:
                ids = _ids_carreras(c, carreras)
                c.execute("DELETE FROM usuario_carrera WHERE usuario_id=?", (uid,))
                c.executemany("INSERT INTO usuario_carrera (usuario_id, carrera_id) VALUES (?,?)",
                              [(uid, cid) for cid in ids])
            if nombre:
                c.execute("UPDATE usuarios SET nombre=? WHERE id=?", (nombre.strip(), uid))
            if correo:
                c.execute("UPDATE usuarios SET correo=? WHERE id=?", (_validar_correo(correo), uid))
            if nuevo_password:
                c.execute("UPDATE usuarios SET password=? WHERE id=?",
                          (_hashear(nuevo_password), uid))
                c.execute("DELETE FROM sesiones WHERE usuario_id=?", (uid,))
            if activo is not None:
                c.execute("UPDATE usuarios SET activo=? WHERE id=?", (int(bool(activo)), uid))
                if not activo:
                    c.execute("DELETE FROM sesiones WHERE usuario_id=?", (uid,))
    except sqlite3.IntegrityError:
        raise ValueError("Ese correo ya esta en uso.")


def borrar_usuario(usuario):
    """Elimina un usuario. Sus sesiones, carreras y chats caen por ON DELETE CASCADE."""
    with bd.transaccion() as c:
        c.execute("DELETE FROM usuarios WHERE usuario=?", (usuario,))


# ---------- sesiones ----------
def login(identificador, password):
    """
    Inicia sesion con usuario O correo. Solo usuarios activos.
    Devuelve el token, o None si las credenciales no son validas.
    """
    ident = (identificador or "").strip()
    with bd.transaccion() as c:
        # de paso, limpia las sesiones ya caducadas
        c.execute("DELETE FROM sesiones WHERE expira_en < datetime('now','localtime')")
        fila = c.execute(
            "SELECT id, password, activo FROM usuarios WHERE usuario=? OR correo=?",
            (ident, ident.lower()),
        ).fetchone()
        if not fila or not fila[2] or not _verificar(password, fila[1]):
            return None
        token = secrets.token_urlsafe(32)
        c.execute("""INSERT INTO sesiones (token, usuario_id, expira_en)
                     VALUES (?, ?, datetime('now','localtime', ?))""",
                  (token, fila[0], f"+{HORAS_SESION} hours"))
    return token


def usuario_de(token):
    """
    Dado un token VIGENTE, devuelve el usuario con sus carreras, o None.
    'carrera' es la primera de la lista (la que se usa por defecto).
    """
    if not token:
        return None
    with bd.transaccion() as c:
        fila = c.execute("""
            SELECT u.id, u.usuario, u.nombre, u.correo, r.nombre
            FROM sesiones s
            JOIN usuarios u ON s.usuario_id = u.id
            JOIN roles r    ON u.rol_id = r.id
            WHERE s.token = ? AND s.expira_en > datetime('now','localtime') AND u.activo = 1
        """, (token,)).fetchone()
        if not fila:
            return None
        carreras = _carreras_de(c, fila[0])
    return {"usuario": fila[1], "nombre": fila[2], "correo": fila[3], "rol": fila[4],
            "carreras": carreras, "carrera": carreras[0] if carreras else None}


def logout(token):
    """Cierra la sesion (borra el token)."""
    with bd.transaccion() as c:
        c.execute("DELETE FROM sesiones WHERE token=?", (token,))


# al importar el modulo se aseguran los usuarios demo
_seed()
