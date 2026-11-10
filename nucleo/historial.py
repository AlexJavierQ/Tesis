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
    Guarda un mensaje en una conversacion y devuelve su id.
    rol: 'user' o 'bot'. citas: lista de {fuente, pagina, seccion,
    documento_id, version} o None.

    Cada cita se guarda en citas_mensaje enlazada a la VERSION EXACTA del
    documento (clave foranea). El JSON de mensajes.citas se sigue escribiendo
    como copia de compatibilidad con la v5.
    """
    with bd.transaccion() as c:
        mid = c.execute(
            "INSERT INTO mensajes (conversacion_id, rol, texto, citas) VALUES (?,?,?,?)",
            (conversacion_id, rol, texto, json.dumps(citas) if citas else None),
        ).lastrowid
        for ci in citas or []:
            fila = c.execute(
                "SELECT id FROM documento_versiones WHERE documento_id=? AND numero=?",
                (ci.get("documento_id"), ci.get("version"))).fetchone()
            if fila:
                c.execute("""INSERT OR IGNORE INTO citas_mensaje
                             (mensaje_id, documento_version_id, pagina, seccion)
                             VALUES (?,?,?,?)""",
                          (mid, fila[0], ci["pagina"], ci.get("seccion") or ""))
    return mid


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


_CAMPOS_CITA = ("fuente", "pagina", "seccion", "documento_id", "version")


def mensajes_de(conversacion_id):
    """
    Lista los mensajes de una conversacion, en orden cronologico.
    Las citas salen de citas_mensaje (la version exacta, por clave foranea).
    Solo si un mensaje antiguo no tiene filas ahi se usa su JSON de la v5.
    """
    with bd.transaccion() as c:
        filas = c.execute("""
            SELECT id, rol, texto, citas, creado_en
            FROM mensajes
            WHERE conversacion_id = ?
            ORDER BY id ASC
        """, (conversacion_id,)).fetchall()
        normalizadas = {}
        for mid, fuente, pagina, seccion, doc_id, version in c.execute("""
                SELECT cm.mensaje_id, d.nombre, cm.pagina, cm.seccion, d.id, v.numero
                FROM citas_mensaje cm
                JOIN mensajes m             ON m.id = cm.mensaje_id
                JOIN documento_versiones v  ON v.id = cm.documento_version_id
                JOIN documentos d           ON d.id = v.documento_id
                WHERE m.conversacion_id = ?
                ORDER BY cm.id""", (conversacion_id,)):
            normalizadas.setdefault(mid, []).append({
                "fuente": fuente, "pagina": pagina, "seccion": seccion,
                "documento_id": doc_id, "version": version})
    salida = []
    for mid, rol, texto, citas, ts in filas:
        legado = [{k: ci.get(k) for k in _CAMPOS_CITA} for ci in (json.loads(citas) if citas else [])]
        salida.append({
            "id": mid,
            "rol": rol,
            "texto": texto,
            "citas": normalizadas.get(mid) or legado,
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
