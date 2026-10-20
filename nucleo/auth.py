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

from nucleo import bd, parametros

ITERACIONES = 200_000   # coste del hash: alto = mas seguro y mas lento
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


def _ids_carreras(c, carreras, rol):
    """
    Convierte nombres de carrera en ids y verifica que existan.
    Todos los roles necesitan al menos una carrera, menos el administrador,
    que trabaja a nivel de sistema.
    """
    if rol == "administrador":
        carreras = carreras or []
    elif not carreras:
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
    """
    Crea los usuarios de demostracion que falten (contrasena demo2026).
    El docente demo queda asignado a los cursos de la carrera por defecto.
    """
    demos = [
        ("estudiante", "Estudiante Demo",    "estudiante@utpl.edu.ec", "estudiante"),
        ("docente",    "Docente Demo",       "docente@utpl.edu.ec",    "docente"),
        ("coord",      "Coordinación Demo",  "coord@utpl.edu.ec",      "coordinacion"),
        ("admin",      "Administrador Demo", "admin@utpl.edu.ec",      "administrador"),
    ]
    for u, nombre, correo, rol in demos:
        if bd.id_usuario(u):
            continue
        carreras = [] if rol == "administrador" else [bd.CARRERA_POR_DEFECTO]
        crear_usuario(u, nombre, correo, "demo2026", rol, carreras)
        if rol == "docente":
            for curso in bd.cursos(bd.CARRERA_POR_DEFECTO):
                bd.asignar_docentes(bd.CARRERA_POR_DEFECTO, curso,
                                    bd.docentes_de_curso(bd.CARRERA_POR_DEFECTO, curso) + [u])


# ---------- CRUD de usuarios ----------
def crear_usuario(usuario, nombre, correo, password, rol, carreras):
    """Alta de un usuario con una o varias carreras. ValueError si algo no es valido."""
    correo = _validar_correo(correo)
    try:
        with bd.transaccion() as c:
            rid = c.execute("SELECT id FROM roles WHERE nombre=?", (rol,)).fetchone()
            if not rid:
                raise ValueError("Rol no valido.")
            ids = _ids_carreras(c, carreras, rol)
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
                if rol != "docente":   # deja de ser docente -> pierde sus cursos asignados
                    c.execute("DELETE FROM curso_docente WHERE usuario_id=?", (uid,))
            if carreras is not None:
                rol_actual = rol or c.execute(
                    "SELECT r.nombre FROM usuarios u JOIN roles r ON u.rol_id = r.id WHERE u.id=?",
                    (uid,)).fetchone()[0]
                ids = _ids_carreras(c, carreras, rol_actual)
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


def datos_de(usuario):
    """{usuario, rol, carreras} de un usuario, o None. Para validar permisos."""
    with bd.transaccion() as c:
        fila = c.execute("""SELECT u.id, r.nombre FROM usuarios u JOIN roles r ON u.rol_id = r.id
                            WHERE u.usuario=?""", (usuario,)).fetchone()
        if not fila:
            return None
        return {"usuario": usuario, "rol": fila[1], "carreras": _carreras_de(c, fila[0])}


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
                  (token, fila[0], f"+{parametros.obtener('horas_sesion')} hours"))
    return token


def usuario_de(token):
    """
    Dado un token VIGENTE, devuelve el usuario con sus carreras, o None.
    'carrera' es la primera de la lista (la que se usa por defecto).
    'cursos_asignados' solo tiene datos para docentes: [{carrera, curso}].
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
            "carreras": carreras, "carrera": carreras[0] if carreras else None,
            "cursos_asignados": bd.cursos_de_docente(fila[1]) if fila[4] == "docente" else []}


def logout(token):
    """Cierra la sesion (borra el token)."""
    with bd.transaccion() as c:
        c.execute("DELETE FROM sesiones WHERE token=?", (token,))


# al importar el modulo se aseguran los usuarios demo
_seed()
