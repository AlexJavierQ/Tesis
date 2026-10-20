# -*- coding: utf-8 -*-
"""
HISTORIAL DE CHAT (persistencia de conversaciones por usuario).

Modelo (definido en nucleo/bd.py):
  conversaciones(id, usuario_id -> usuarios, titulo, iniciada_en)
  mensajes(id, conversacion_id -> conversaciones, rol, texto, citas, creado_en)

Las fechas las pone la propia BD (columnas DATETIME con valor por defecto).

El historial esta ligado al usuario: cada quien ve y gestiona solo sus
propias conversaciones.
"""
import json

from nucleo import bd


def crear_conversacion(usuario, titulo=""):
    """Crea una conversacion vacia para el usuario y devuelve su id."""
    uid = bd.id_usuario(usuario)
    if not uid:
        raise ValueError("Usuario no encontrado.")
    titulo = (titulo or "Nueva conversación").strip()[:80]
    with bd.transaccion() as c:
        return c.execute(
            "INSERT INTO conversaciones (usuario_id, titulo) VALUES (?,?)", (uid, titulo)
        ).lastrowid


def agregar_mensaje(conversacion_id, rol, texto, citas=None):
    """
    Guarda un mensaje en una conversacion.
    rol: 'user' o 'bot'. citas: lista (se guarda como JSON) o None.
    """
    with bd.transaccion() as c:
        c.execute(
            "INSERT INTO mensajes (conversacion_id, rol, texto, citas) VALUES (?,?,?,?)",
            (conversacion_id, rol, texto, json.dumps(citas) if citas else None),
        )


def es_dueno(conversacion_id, usuario):
    """True si la conversacion pertenece a ese usuario (control de acceso)."""
    uid = bd.id_usuario(usuario)
    if not uid:
        return False
    with bd.transaccion() as c:
        fila = c.execute(
            "SELECT 1 FROM conversaciones WHERE id=? AND usuario_id=?",
            (conversacion_id, uid),
        ).fetchone()
    return fila is not None


def conversaciones_de(usuario):
    """Lista las conversaciones del usuario (mas reciente primero)."""
    uid = bd.id_usuario(usuario)
    if not uid:
        return []
    with bd.transaccion() as c:
        filas = c.execute("""
        SELECT co.id, co.titulo, co.iniciada_en, COUNT(m.id) AS n
        FROM conversaciones co
        LEFT JOIN mensajes m ON m.conversacion_id = co.id
        WHERE co.usuario_id = ?
        GROUP BY co.id
        ORDER BY co.id DESC
        """, (uid,)).fetchall()
    return [{"id": f[0], "titulo": f[1], "iniciada_en": f[2], "mensajes": f[3]}
            for f in filas]


def mensajes_de(conversacion_id):
    """Lista los mensajes de una conversacion, en orden cronologico."""
    with bd.transaccion() as c:
        filas = c.execute("""
            SELECT id, rol, texto, citas, creado_en
            FROM mensajes
            WHERE conversacion_id = ?
            ORDER BY id ASC
        """, (conversacion_id,)).fetchall()
    salida = []
    for mid, rol, texto, citas, ts in filas:
        salida.append({
            "id": mid,
            "rol": rol,
            "texto": texto,
            "citas": json.loads(citas) if citas else [],
            "ts": ts,
        })
    return salida


def resumen_de(conversacion_id):
    """(resumen, id del ultimo mensaje incluido) de la memoria de una conversacion."""
    with bd.transaccion() as c:
        fila = c.execute("SELECT resumen, resumen_hasta FROM conversaciones WHERE id=?",
                         (conversacion_id,)).fetchone()
    return (fila[0] or "", fila[1]) if fila else ("", 0)


def guardar_resumen(conversacion_id, resumen, hasta):
    """Guarda el resumen actualizado y hasta que mensaje cubre."""
    with bd.transaccion() as c:
        c.execute("UPDATE conversaciones SET resumen=?, resumen_hasta=? WHERE id=?",
                  (resumen, hasta, conversacion_id))


def borrar_conversacion(conversacion_id):
    """Borra una conversacion (sus mensajes caen por ON DELETE CASCADE)."""
    with bd.transaccion() as c:
        c.execute("DELETE FROM conversaciones WHERE id=?", (conversacion_id,))
