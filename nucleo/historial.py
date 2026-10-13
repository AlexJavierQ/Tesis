# -*- coding: utf-8 -*-
"""
HISTORIAL DE CHAT (persistencia de conversaciones por usuario).

Modelo (definido en nucleo/bd.py):
  conversaciones(id, usuario_id -> usuarios, titulo, iniciada_en)
  mensajes(id, conversacion_id -> conversaciones, rol, texto, citas, ts)

A diferencia de las metricas (anonimas), el historial SI esta ligado al
usuario: cada quien ve y gestiona solo sus propias conversaciones. Las
metricas agregadas siguen siendo anonimas; esto es lo contrario: privado
de cada usuario.
"""
import json
import datetime as dt

from nucleo import bd


def _ahora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def crear_conversacion(usuario, titulo=""):
    """Crea una conversacion vacia para el usuario y devuelve su id."""
    uid = bd.id_usuario(usuario)
    if not uid:
        raise ValueError("Usuario no encontrado.")
    titulo = (titulo or "Nueva conversación").strip()[:80]
    c = bd.conexion()
    cur = c.execute(
        "INSERT INTO conversaciones (usuario_id, titulo, iniciada_en) VALUES (?,?,?)",
        (uid, titulo, _ahora()),
    )
    cid = cur.lastrowid
    c.commit()
    c.close()
    return cid


def agregar_mensaje(conversacion_id, rol, texto, citas=None):
    """
    Guarda un mensaje en una conversacion.
    rol: 'user' o 'bot'. citas: lista (se guarda como JSON) o None.
    """
    c = bd.conexion()
    c.execute(
        "INSERT INTO mensajes (conversacion_id, rol, texto, citas, ts) VALUES (?,?,?,?,?)",
        (conversacion_id, rol, texto,
         json.dumps(citas) if citas else None, _ahora()),
    )
    c.commit()
    c.close()


def es_dueno(conversacion_id, usuario):
    """True si la conversacion pertenece a ese usuario (control de acceso)."""
    uid = bd.id_usuario(usuario)
    if not uid:
        return False
    c = bd.conexion()
    fila = c.execute(
        "SELECT 1 FROM conversaciones WHERE id=? AND usuario_id=?",
        (conversacion_id, uid),
    ).fetchone()
    c.close()
    return fila is not None


def conversaciones_de(usuario):
    """Lista las conversaciones del usuario (mas reciente primero)."""
    uid = bd.id_usuario(usuario)
    if not uid:
        return []
    c = bd.conexion()
    filas = c.execute("""
        SELECT co.id, co.titulo, co.iniciada_en, COUNT(m.id) AS n
        FROM conversaciones co
        LEFT JOIN mensajes m ON m.conversacion_id = co.id
        WHERE co.usuario_id = ?
        GROUP BY co.id
        ORDER BY co.id DESC
    """, (uid,)).fetchall()
    c.close()
    return [{"id": f[0], "titulo": f[1], "iniciada_en": f[2], "mensajes": f[3]}
            for f in filas]


def mensajes_de(conversacion_id):
    """Lista los mensajes de una conversacion, en orden cronologico."""
    c = bd.conexion()
    filas = c.execute("""
        SELECT rol, texto, citas, ts
        FROM mensajes
        WHERE conversacion_id = ?
        ORDER BY id ASC
    """, (conversacion_id,)).fetchall()
    c.close()
    salida = []
    for rol, texto, citas, ts in filas:
        salida.append({
            "rol": rol,
            "texto": texto,
            "citas": json.loads(citas) if citas else [],
            "ts": ts,
        })
    return salida


def borrar_conversacion(conversacion_id):
    """Borra una conversacion (sus mensajes caen por ON DELETE CASCADE)."""
    c = bd.conexion()
    c.execute("DELETE FROM conversaciones WHERE id=?", (conversacion_id,))
    c.commit()
    c.close()
