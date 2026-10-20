# -*- coding: utf-8 -*-
"""
MODELO DE DATOS RELACIONAL (SQLite normalizado) - version 4.

Es la FUENTE DE VERDAD del sistema. Todas las tablas viven en un solo archivo
(datos/sistema.db) y se relacionan por claves foraneas (FK). Los vectores del
RAG siguen en ChromaDB; los PDF siguen en carpetas (datos/docs/...).

Tablas (15):
  ESTRUCTURA ACADEMICA
    facultades(id, nombre)
    carreras(id, facultad_id -> facultades, nombre)
    cursos(id, carrera_id -> carreras, nombre)
    curso_docente(curso_id -> cursos, usuario_id -> usuarios)          N:M
  USUARIOS Y ACCESO
    roles(id, nombre)
    usuarios(id, usuario, nombre, correo, password, rol_id -> roles, activo, creado_en)
    usuario_carrera(usuario_id -> usuarios, carrera_id -> carreras)   N:M
    sesiones(token, usuario_id -> usuarios, creado_en, expira_en)
  DOCUMENTOS DEL RAG
    documentos(id, carrera_id, curso_id (NULL = global), nombre, activo, creado_en)
    documento_versiones(id, documento_id -> documentos, numero, ruta,
                        fragmentos, subido_por -> usuarios, subido_en,
                        restaurada_de)  <- numero de la version que se restauro
  CONFIGURACION DEL SISTEMA (la edita el administrador desde la interfaz)
    parametros(clave, valor, tipo, minimo, maximo, descripcion,
               actualizado_por -> usuarios, actualizado_en)
  CHAT
    conversaciones(id, usuario_id -> usuarios, titulo, iniciada_en,
                   resumen, resumen_hasta)   <- memoria conversacional
    mensajes(id, conversacion_id -> conversaciones, rol, texto, citas, creado_en)
  ANALITICA Y AUDITORIA
    consultas(id, carrera_id, curso_id, usuario_id, modo, pregunta, respondida, creado_en)
    logs(id, usuario_id, accion, detalle, creado_en)

ROBUSTEZ:
  - Fechas declaradas como DATETIME, con valor por defecto y un CHECK que
    rechaza cualquier texto que no sea una fecha valida.
  - CHECK en los campos con valores cerrados (activo 0/1, rol del mensaje,
    modo de consulta, formato de correo).
  - Claves foraneas activas en cada conexion y ON DELETE definido en cada una.
  - Cada operacion corre en una TRANSACCION: o se guarda todo o nada.
"""
import os
import sqlite3
from contextlib import contextmanager

BASE = os.path.dirname(__file__)
DB = os.path.join(os.path.dirname(BASE), "datos", "sistema.db")
DOCS = os.path.join(os.path.dirname(BASE), "datos", "docs")
CONSULTAS_VIEJA = os.path.join(os.path.dirname(BASE), "datos", "consultas.db")

VERSION_ESQUEMA = 4
ROLES = ("estudiante", "docente", "coordinacion", "administrador")
FACULTAD_POR_DEFECTO = "Ingenierías y Arquitectura"
CARRERA_POR_DEFECTO = "computacion"


def conexion():
    """
    Abre una conexion a la BD relacional.
    OJO: SQLite trae las claves foraneas DESACTIVADAS por defecto. Hay que
    encenderlas en CADA conexion con el PRAGMA, si no las FK no se verifican.
    """
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, check_same_thread=False, timeout=10)
    c.execute("PRAGMA foreign_keys = ON")
    return c


@contextmanager
def transaccion():
    """
    Uso:  with bd.transaccion() as c:  c.execute(...)
    Si todo sale bien hace COMMIT; si algo lanza un error hace ROLLBACK
    (no queda nada a medias) y siempre cierra la conexion.
    """
    c = conexion()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def _fecha(col):
    """Columna de fecha: tipo DATETIME, se llena sola y solo acepta fechas validas."""
    return (f"{col} DATETIME NOT NULL DEFAULT (datetime('now','localtime')) "
            f"CHECK ({col} IS datetime({col}))")


# ---------- creacion del esquema ----------
def _crear_tablas(c):
    # --- estructura academica ---
    c.execute("""CREATE TABLE IF NOT EXISTS facultades (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT UNIQUE NOT NULL CHECK (length(trim(nombre)) > 0)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS carreras (
        id           INTEGER PRIMARY KEY,
        facultad_id  INTEGER NOT NULL REFERENCES facultades(id) ON DELETE RESTRICT,
        nombre       TEXT UNIQUE NOT NULL CHECK (length(trim(nombre)) > 0)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cursos (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        nombre      TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
        UNIQUE (carrera_id, nombre)
    )""")
    # que docentes dictan cada curso (la coordinacion los asigna)
    c.execute("""CREATE TABLE IF NOT EXISTS curso_docente (
        curso_id    INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        PRIMARY KEY (curso_id, usuario_id)
    )""")

    # --- usuarios y acceso ---
    c.execute("""CREATE TABLE IF NOT EXISTS roles (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT UNIQUE NOT NULL
    )""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS usuarios (
        id        INTEGER PRIMARY KEY,
        usuario   TEXT UNIQUE NOT NULL CHECK (length(trim(usuario)) > 0),
        nombre    TEXT NOT NULL,
        correo    TEXT UNIQUE NOT NULL CHECK (correo LIKE '%_@_%._%'),
        password  TEXT NOT NULL,
        rol_id    INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
        activo    INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        {_fecha("creado_en")}
    )""")
    # un usuario puede pertenecer a MUCHAS carreras (relacion N:M)
    c.execute("""CREATE TABLE IF NOT EXISTS usuario_carrera (
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        PRIMARY KEY (usuario_id, carrera_id)
    )""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS sesiones (
        token       TEXT PRIMARY KEY,
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        {_fecha("creado_en")},
        expira_en   DATETIME NOT NULL CHECK (expira_en IS datetime(expira_en))
    )""")

    # --- documentos del RAG ---
    # el DOCUMENTO es la entidad estable ("Reglamento de Practicum");
    # cada vez que se sube de nuevo se agrega una VERSION. curso_id NULL = global.
    c.execute(f"""CREATE TABLE IF NOT EXISTS documentos (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        curso_id    INTEGER REFERENCES cursos(id) ON DELETE CASCADE,
        nombre      TEXT NOT NULL,
        activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        {_fecha("creado_en")}
    )""")
    # UNIQUE normal no sirve aqui: en SQLite dos NULL no se consideran iguales.
    # Con IFNULL, dos documentos globales con el mismo nombre si chocan.
    c.execute("""CREATE UNIQUE INDEX IF NOT EXISTS ux_documento_ambito
        ON documentos (carrera_id, IFNULL(curso_id, 0), nombre)""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS documento_versiones (
        id            INTEGER PRIMARY KEY,
        documento_id  INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
        numero        INTEGER NOT NULL CHECK (numero >= 1),
        ruta          TEXT UNIQUE NOT NULL,
        fragmentos    INTEGER NOT NULL DEFAULT 0 CHECK (fragmentos >= 0),
        subido_por    INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        {_fecha("subido_en")},
        restaurada_de INTEGER,      -- NULL = subida normal; N = copia de la version N
        UNIQUE (documento_id, numero)
    )""")

    # --- chat ---
    # resumen / resumen_hasta: memoria conversacional. Los mensajes antiguos
    # (los que ya no entran en la ventana reciente) se condensan en `resumen`;
    # `resumen_hasta` es el id del ultimo mensaje incluido en el.
    c.execute(f"""CREATE TABLE IF NOT EXISTS conversaciones (
        id             INTEGER PRIMARY KEY,
        usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        titulo         TEXT NOT NULL,
        {_fecha("iniciada_en")},
        resumen        TEXT,
        resumen_hasta  INTEGER NOT NULL DEFAULT 0
    )""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS mensajes (
        id               INTEGER PRIMARY KEY,
        conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
        rol              TEXT NOT NULL CHECK (rol IN ('user', 'bot')),
        texto            TEXT NOT NULL,
        citas            TEXT,              -- JSON de citas (solo mensajes del bot)
        {_fecha("creado_en")}
    )""")

    # --- analitica y auditoria ---
    # consultas ya NO esta aislada: se relaciona con carrera, curso y usuario.
    # usuario_id es NULL cuando pregunta alguien sin sesion (widget publico).
    c.execute(f"""CREATE TABLE IF NOT EXISTS consultas (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        curso_id    INTEGER REFERENCES cursos(id) ON DELETE SET NULL,
        usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        modo        TEXT NOT NULL CHECK (modo IN ('general', 'curso', 'ambos')),
        pregunta    TEXT NOT NULL,
        respondida  INTEGER NOT NULL CHECK (respondida IN (0, 1)),
        {_fecha("creado_en")}
    )""")
    # bitacora: quien hizo que y cuando (login, altas, bajas, documentos...)
    c.execute(f"""CREATE TABLE IF NOT EXISTS logs (
        id          INTEGER PRIMARY KEY,
        usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        accion      TEXT NOT NULL,
        detalle     TEXT,
        {_fecha("creado_en")}
    )""")

    # --- configuracion del sistema ---
    # parametros que antes estaban escritos en el codigo. tipo + minimo/maximo
    # permiten validar el valor antes de guardarlo.
    c.execute(f"""CREATE TABLE IF NOT EXISTS parametros (
        clave            TEXT PRIMARY KEY,
        valor            TEXT NOT NULL,
        tipo             TEXT NOT NULL CHECK (tipo IN ('entero', 'decimal', 'texto')),
        minimo           REAL,
        maximo           REAL,
        descripcion      TEXT NOT NULL,
        actualizado_por  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        {_fecha("actualizado_en")}
    )""")

    # indices sobre las FK mas consultadas (aceleran los JOIN y filtros)
    for sql in (
        "CREATE INDEX IF NOT EXISTS ix_cursos_carrera ON cursos(carrera_id)",
        "CREATE INDEX IF NOT EXISTS ix_curso_docente_usuario ON curso_docente(usuario_id)",
        "CREATE INDEX IF NOT EXISTS ix_versiones_doc ON documento_versiones(documento_id)",
        "CREATE INDEX IF NOT EXISTS ix_conv_usuario ON conversaciones(usuario_id)",
        "CREATE INDEX IF NOT EXISTS ix_mensajes_conv ON mensajes(conversacion_id)",
        "CREATE INDEX IF NOT EXISTS ix_consultas_carrera ON consultas(carrera_id, curso_id)",
        "CREATE INDEX IF NOT EXISTS ix_logs_fecha ON logs(creado_en)",
    ):
        c.execute(sql)


def _migrar_si_hace_falta(c):
    """
    Lleva una sistema.db antigua a la version actual del esquema.
      v1 -> se recrea entera (era otro modelo y solo tenia datos demo).
      v2 -> v3: cambios aditivos. Las tablas nuevas las crea _crear_tablas;
               aqui solo se agrega la columna nueva. No se pierde nada.
      v3 -> v4: columnas del resumen de la memoria conversacional.
    """
    version = c.execute("PRAGMA user_version").fetchone()[0]
    tablas = [f[0] for f in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    if version < 2 and tablas:
        print("[bd] Esquema v1 detectado: se recrea sistema.db.")
        c.execute("PRAGMA foreign_keys = OFF")
        for t in tablas:
            c.execute(f'DROP TABLE IF EXISTS "{t}"')
        c.execute("PRAGMA foreign_keys = ON")
        return
    if version == 2:
        print("[bd] Migrando sistema.db de v2 a v3.")
        c.execute("ALTER TABLE documento_versiones ADD COLUMN restaurada_de INTEGER")
    if version in (2, 3):
        print("[bd] Migrando sistema.db a v4 (memoria conversacional).")
        c.execute("ALTER TABLE conversaciones ADD COLUMN resumen TEXT")
        c.execute("ALTER TABLE conversaciones ADD COLUMN resumen_hasta INTEGER NOT NULL DEFAULT 0")


def _seed(c):
    """
    Datos iniciales:
    - roles fijos y la facultad por defecto.
    - carreras y cursos que ya existan como carpetas en datos/docs/ (asi no
      se pierde la estructura creada antes, p. ej. el curso 'Practicum 2').
    (Los usuarios demo los siembra auth.py.)
    """
    for r in ROLES:
        c.execute("INSERT OR IGNORE INTO roles (nombre) VALUES (?)", (r,))
    c.execute("INSERT OR IGNORE INTO facultades (nombre) VALUES (?)", (FACULTAD_POR_DEFECTO,))
    fid = c.execute("SELECT id FROM facultades WHERE nombre=?",
                    (FACULTAD_POR_DEFECTO,)).fetchone()[0]

    carreras_disco = [CARRERA_POR_DEFECTO]
    if os.path.isdir(DOCS):
        carreras_disco += [d for d in sorted(os.listdir(DOCS))
                           if os.path.isdir(os.path.join(DOCS, d))]
    for carrera in carreras_disco:
        c.execute("INSERT OR IGNORE INTO carreras (facultad_id, nombre) VALUES (?,?)",
                  (fid, carrera))
        cid = c.execute("SELECT id FROM carreras WHERE nombre=?", (carrera,)).fetchone()[0]
        cursos_dir = os.path.join(DOCS, carrera, "cursos")
        if os.path.isdir(cursos_dir):
            for curso in sorted(os.listdir(cursos_dir)):
                if os.path.isdir(os.path.join(cursos_dir, curso)):
                    c.execute("INSERT OR IGNORE INTO cursos (carrera_id, nombre) VALUES (?,?)",
                              (cid, curso))


def _importar_consultas_viejas(c):
    """
    Las consultas antes vivian aisladas en datos/consultas.db. Si ese archivo
    existe, se copian sus filas a la tabla consultas (ya relacionada) y el
    archivo se renombra para no importarlo dos veces.
    """
    if not os.path.exists(CONSULTAS_VIEJA):
        return
    vieja = sqlite3.connect(CONSULTAS_VIEJA)
    try:
        filas = vieja.execute("SELECT ts, pregunta, respondida, ambito FROM consultas").fetchall()
    except sqlite3.Error:
        filas = []
    vieja.close()
    for ts, pregunta, respondida, ambito in filas:
        carrera, _, resto = (ambito or "").partition("|")
        caid = c.execute("SELECT id FROM carreras WHERE nombre=?", (carrera,)).fetchone()
        if not caid or not pregunta:
            continue
        cuid, modo = None, "general"
        if resto.startswith("curso:"):
            fila = c.execute("SELECT id FROM cursos WHERE carrera_id=? AND nombre=?",
                             (caid[0], resto[6:])).fetchone()
            cuid, modo = (fila[0] if fila else None), "ambos"
        c.execute("INSERT INTO consultas (carrera_id, curso_id, modo, pregunta, respondida, creado_en) "
                  "VALUES (?,?,?,?,?,datetime(?))",
                  (caid[0], cuid, modo, pregunta, int(bool(respondida)), ts))
    os.replace(CONSULTAS_VIEJA, CONSULTAS_VIEJA + ".migrada")


def inicializar():
    with transaccion() as c:
        version_previa = c.execute("PRAGMA user_version").fetchone()[0]
        _migrar_si_hace_falta(c)
        _crear_tablas(c)
        _seed(c)
        _importar_consultas_viejas(c)
        if version_previa == 2:
            # en v2 un docente gestionaba todos los cursos de su carrera; al
            # migrar se le asignan esos cursos para que no pierda el acceso
            c.execute("""INSERT OR IGNORE INTO curso_docente (curso_id, usuario_id)
                         SELECT cu.id, u.id FROM usuarios u
                         JOIN roles r ON u.rol_id = r.id
                         JOIN usuario_carrera uc ON uc.usuario_id = u.id
                         JOIN cursos cu ON cu.carrera_id = uc.carrera_id
                         WHERE r.nombre = 'docente'""")
        c.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")


# ---------- helpers de ids ----------
def _id(c, sql, params):
    fila = c.execute(sql, params).fetchone()
    return fila[0] if fila else None


def id_rol(nombre):
    with transaccion() as c:
        return _id(c, "SELECT id FROM roles WHERE nombre=?", (nombre,))


def id_usuario(usuario):
    with transaccion() as c:
        return _id(c, "SELECT id FROM usuarios WHERE usuario=?", (usuario,))


def id_carrera(nombre):
    with transaccion() as c:
        return _id(c, "SELECT id FROM carreras WHERE nombre=?", (nombre,))


def id_curso(carrera, curso):
    with transaccion() as c:
        return _id(c, """SELECT cu.id FROM cursos cu JOIN carreras ca ON cu.carrera_id = ca.id
                         WHERE ca.nombre=? AND cu.nombre=?""", (carrera, curso))


# ---------- estructura: facultades ----------
def facultades():
    """Facultades con sus carreras: [{nombre, carreras: [...]}]."""
    with transaccion() as c:
        filas = c.execute("""
            SELECT f.nombre, ca.nombre
            FROM facultades f LEFT JOIN carreras ca ON ca.facultad_id = f.id
            ORDER BY f.nombre, ca.nombre""").fetchall()
    salida = {}
    for fac, car in filas:
        salida.setdefault(fac, [])
        if car:
            salida[fac].append(car)
    return [{"nombre": f, "carreras": cs} for f, cs in salida.items()]


def crear_facultad(nombre):
    try:
        with transaccion() as c:
            c.execute("INSERT INTO facultades (nombre) VALUES (?)", (nombre,))
    except sqlite3.IntegrityError:
        raise ValueError("Esa facultad ya existe.")


# ---------- estructura: carreras ----------
def carreras():
    """Nombres de todas las carreras (orden alfabetico)."""
    with transaccion() as c:
        return [f[0] for f in c.execute("SELECT nombre FROM carreras ORDER BY nombre")]


def facultad_de(carrera):
    """Nombre de la facultad a la que pertenece una carrera."""
    with transaccion() as c:
        return _id(c, """SELECT f.nombre FROM carreras ca JOIN facultades f
                         ON ca.facultad_id = f.id WHERE ca.nombre=?""", (carrera,))


def crear_carrera(nombre, facultad=FACULTAD_POR_DEFECTO):
    """Alta de una carrera dentro de una facultad."""
    with transaccion() as c:
        fid = _id(c, "SELECT id FROM facultades WHERE nombre=?", (facultad,))
        if not fid:
            raise ValueError("Facultad no encontrada.")
        try:
            c.execute("INSERT INTO carreras (facultad_id, nombre) VALUES (?,?)", (fid, nombre))
        except sqlite3.IntegrityError:
            raise ValueError("Esa carrera ya existe.")


# ---------- estructura: cursos ----------
def cursos(carrera):
    """Nombres de los cursos de una carrera (JOIN cursos-carreras)."""
    with transaccion() as c:
        return [f[0] for f in c.execute("""
            SELECT cu.nombre FROM cursos cu JOIN carreras ca ON cu.carrera_id = ca.id
            WHERE ca.nombre = ? ORDER BY cu.nombre""", (carrera,))]


def crear_curso(carrera, nombre):
    """Alta de un curso dentro de una carrera. ValueError si ya existe."""
    cid = id_carrera(carrera)
    if not cid:
        raise ValueError("Carrera no encontrada.")
    try:
        with transaccion() as c:
            c.execute("INSERT INTO cursos (carrera_id, nombre) VALUES (?,?)", (cid, nombre))
    except sqlite3.IntegrityError:
        raise ValueError("Ese curso ya existe.")


def docentes_de_curso(carrera, curso):
    """Usuarios (docentes) asignados a un curso."""
    with transaccion() as c:
        return [f[0] for f in c.execute("""
            SELECT u.usuario FROM curso_docente cd
            JOIN usuarios u  ON cd.usuario_id = u.id
            JOIN cursos cu   ON cd.curso_id = cu.id
            JOIN carreras ca ON cu.carrera_id = ca.id
            WHERE ca.nombre=? AND cu.nombre=? ORDER BY u.usuario""", (carrera, curso))]


def asignar_docentes(carrera, curso, usuarios):
    """
    Reemplaza la lista de docentes de un curso. Cada uno debe tener rol
    docente y pertenecer a la carrera del curso.
    """
    cuid = id_curso(carrera, curso)
    if not cuid:
        raise ValueError("Curso no encontrado.")
    with transaccion() as c:
        ids = []
        for u in usuarios:
            fila = c.execute("""
                SELECT u.id FROM usuarios u
                JOIN roles r ON u.rol_id = r.id
                JOIN usuario_carrera uc ON uc.usuario_id = u.id
                JOIN carreras ca ON uc.carrera_id = ca.id
                WHERE u.usuario=? AND r.nombre='docente' AND ca.nombre=?""",
                (u, carrera)).fetchone()
            if not fila:
                raise ValueError(f"'{u}' no es docente de {carrera}.")
            ids.append(fila[0])
        c.execute("DELETE FROM curso_docente WHERE curso_id=?", (cuid,))
        c.executemany("INSERT INTO curso_docente (curso_id, usuario_id) VALUES (?,?)",
                      [(cuid, i) for i in ids])


def cursos_de_docente(usuario):
    """Cursos asignados a un docente: [{carrera, curso}]."""
    with transaccion() as c:
        filas = c.execute("""
            SELECT ca.nombre, cu.nombre FROM curso_docente cd
            JOIN usuarios u  ON cd.usuario_id = u.id
            JOIN cursos cu   ON cd.curso_id = cu.id
            JOIN carreras ca ON cu.carrera_id = ca.id
            WHERE u.usuario=? ORDER BY ca.nombre, cu.nombre""", (usuario,)).fetchall()
    return [{"carrera": f[0], "curso": f[1]} for f in filas]


# ---------- documentos y versiones ----------
_SQL_DOC = """
    SELECT d.id, d.nombre, d.activo, v.numero, v.ruta, v.fragmentos, v.subido_en,
           (SELECT COUNT(*) FROM documento_versiones x WHERE x.documento_id = d.id)
    FROM documentos d
    JOIN documento_versiones v ON v.documento_id = d.id
    WHERE v.numero = (SELECT MAX(numero) FROM documento_versiones
                      WHERE documento_id = d.id)
"""


def _doc_dict(f):
    return {"id": f[0], "nombre": f[1], "activo": bool(f[2]), "version": f[3],
            "ruta": f[4], "fragmentos": f[5], "subido_en": f[6], "versiones": f[7]}


def documento(carrera, curso, nombre):
    """El documento (con su version vigente) de un ambito, o None."""
    caid = id_carrera(carrera)
    cuid = id_curso(carrera, curso) if curso else None
    with transaccion() as c:
        f = c.execute(_SQL_DOC + " AND d.carrera_id=? AND IFNULL(d.curso_id,0)=? AND d.nombre=?",
                      (caid, cuid or 0, nombre)).fetchone()
    return _doc_dict(f) if f else None


def documento_por_id(doc_id):
    with transaccion() as c:
        f = c.execute(_SQL_DOC + " AND d.id=?", (doc_id,)).fetchone()
        if not f:
            return None
        d = _doc_dict(f)
        amb = c.execute("""SELECT ca.nombre, cu.nombre FROM documentos d
                           JOIN carreras ca ON d.carrera_id = ca.id
                           LEFT JOIN cursos cu ON d.curso_id = cu.id
                           WHERE d.id=?""", (doc_id,)).fetchone()
    d["carrera"], d["curso"] = amb
    return d


def documentos_de(carrera, curso=None):
    """Documentos de un ambito (global de la carrera, o de un curso), version vigente."""
    caid = id_carrera(carrera)
    if not caid:
        return []
    cuid = id_curso(carrera, curso) if curso else None
    with transaccion() as c:
        filas = c.execute(_SQL_DOC + " AND d.carrera_id=? AND IFNULL(d.curso_id,0)=? ORDER BY d.nombre",
                          (caid, cuid or 0)).fetchall()
    return [_doc_dict(f) for f in filas]


def registrar_version(carrera, curso, nombre, ruta, fragmentos, usuario=None,
                      restaurada_de=None):
    """
    Registra una nueva version de un documento. Si el documento no existe,
    lo crea (version 1). Devuelve el numero de version asignado.
    """
    caid = id_carrera(carrera)
    if not caid:
        raise ValueError("Carrera no encontrada.")
    cuid = id_curso(carrera, curso) if curso else None
    if curso and not cuid:
        raise ValueError("Curso no encontrado.")
    uid = id_usuario(usuario) if usuario else None
    with transaccion() as c:
        doc_id = _id(c, "SELECT id FROM documentos WHERE carrera_id=? AND IFNULL(curso_id,0)=? AND nombre=?",
                     (caid, cuid or 0, nombre))
        if not doc_id:
            doc_id = c.execute("INSERT INTO documentos (carrera_id, curso_id, nombre) VALUES (?,?,?)",
                               (caid, cuid, nombre)).lastrowid
        numero = 1 + (_id(c, "SELECT MAX(numero) FROM documento_versiones WHERE documento_id=?",
                          (doc_id,)) or 0)
        c.execute("""INSERT INTO documento_versiones
                     (documento_id, numero, ruta, fragmentos, subido_por, restaurada_de)
                     VALUES (?,?,?,?,?,?)""",
                  (doc_id, numero, ruta, fragmentos, uid, restaurada_de))
    return numero


def actualizar_fragmentos(ruta, fragmentos):
    """Al reindexar, actualiza cuantos fragmentos genero la version vigente."""
    with transaccion() as c:
        c.execute("UPDATE documento_versiones SET fragmentos=? WHERE ruta=?", (fragmentos, ruta))


def mover_version(ruta_vieja, ruta_nueva):
    """Una version anterior se archiva en otra carpeta: se actualiza su ruta."""
    with transaccion() as c:
        c.execute("UPDATE documento_versiones SET ruta=? WHERE ruta=?", (ruta_nueva, ruta_vieja))


def versiones_de(doc_id):
    """Historial de versiones de un documento (la mas nueva primero)."""
    with transaccion() as c:
        filas = c.execute("""
            SELECT v.numero, v.ruta, v.fragmentos, v.subido_en, u.usuario, v.restaurada_de
            FROM documento_versiones v LEFT JOIN usuarios u ON v.subido_por = u.id
            WHERE v.documento_id=? ORDER BY v.numero DESC""", (doc_id,)).fetchall()
    return [{"numero": f[0], "ruta": f[1], "fragmentos": f[2], "subido_en": f[3],
             "subido_por": f[4] or "—", "restaurada_de": f[5]} for f in filas]


def cambiar_estado_documento(doc_id, activo):
    with transaccion() as c:
        c.execute("UPDATE documentos SET activo=? WHERE id=?", (int(bool(activo)), doc_id))


def borrar_documento(doc_id):
    """Borra el documento (sus versiones caen por CASCADE). Devuelve las rutas de sus archivos."""
    with transaccion() as c:
        rutas = [f[0] for f in c.execute(
            "SELECT ruta FROM documento_versiones WHERE documento_id=?", (doc_id,))]
        c.execute("DELETE FROM documentos WHERE id=?", (doc_id,))
    return rutas


def esta_inactivo(ruta):
    """True si la ruta pertenece a un documento desactivado (no se debe indexar)."""
    with transaccion() as c:
        return _id(c, """SELECT 1 FROM documento_versiones v JOIN documentos d
                         ON v.documento_id = d.id WHERE v.ruta=? AND d.activo=0""",
                   (ruta,)) is not None


# ---------- bitacora (logs) ----------
def log(accion, detalle="", usuario=None):
    """Anota en la bitacora quien hizo que. usuario=None -> accion anonima/sistema."""
    uid = id_usuario(usuario) if usuario else None
    with transaccion() as c:
        c.execute("INSERT INTO logs (usuario_id, accion, detalle) VALUES (?,?,?)",
                  (uid, accion, detalle))


def logs(limite=200):
    """Ultimas entradas de la bitacora."""
    with transaccion() as c:
        filas = c.execute("""
            SELECT l.creado_en, IFNULL(u.usuario, '—'), l.accion, IFNULL(l.detalle, '')
            FROM logs l LEFT JOIN usuarios u ON l.usuario_id = u.id
            ORDER BY l.id DESC LIMIT ?""", (limite,)).fetchall()
    return [{"fecha": f[0], "usuario": f[1], "accion": f[2], "detalle": f[3]} for f in filas]


# al importar el modulo se asegura el esquema y los datos iniciales
inicializar()
