-- Esquema v5 de sistema.db (solo estructura, sin datos), tal como lo creaba
-- nucleo/bd.py antes de la migracion v6. Lo usa pruebas/test_v1_seguridad.py
-- para construir una base v5 sintetica y comprobar la migracion a v6.

CREATE TABLE facultades (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT UNIQUE NOT NULL CHECK (length(trim(nombre)) > 0)
    );

CREATE TABLE carreras (
        id           INTEGER PRIMARY KEY,
        facultad_id  INTEGER NOT NULL REFERENCES facultades(id) ON DELETE RESTRICT,
        nombre       TEXT UNIQUE NOT NULL CHECK (length(trim(nombre)) > 0)
    );

CREATE TABLE cursos (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        nombre      TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
        UNIQUE (carrera_id, nombre)
    );

CREATE TABLE curso_docente (
        curso_id    INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        PRIMARY KEY (curso_id, usuario_id)
    );

CREATE TABLE roles (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT UNIQUE NOT NULL
    );

CREATE TABLE usuarios (
        id        INTEGER PRIMARY KEY,
        usuario   TEXT UNIQUE NOT NULL CHECK (length(trim(usuario)) > 0),
        nombre    TEXT NOT NULL,
        correo    TEXT UNIQUE NOT NULL CHECK (correo LIKE '%_@_%._%'),
        password  TEXT NOT NULL,
        rol_id    INTEGER NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
        activo    INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        creado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (creado_en IS datetime(creado_en))
    );

CREATE TABLE usuario_carrera (
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        PRIMARY KEY (usuario_id, carrera_id)
    );

CREATE TABLE sesiones (
        token       TEXT PRIMARY KEY,
        usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        creado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (creado_en IS datetime(creado_en)),
        expira_en   DATETIME NOT NULL CHECK (expira_en IS datetime(expira_en))
    );

CREATE TABLE documentos (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        curso_id    INTEGER REFERENCES cursos(id) ON DELETE CASCADE,
        nombre      TEXT NOT NULL,
        activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        vigencia    TEXT,           -- p. ej. "Periodo abril-agosto 2024 (historico)"
        creado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (creado_en IS datetime(creado_en))
    );

CREATE TABLE documento_versiones (
        id            INTEGER PRIMARY KEY,
        documento_id  INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
        numero        INTEGER NOT NULL CHECK (numero >= 1),
        ruta          TEXT UNIQUE NOT NULL,
        fragmentos    INTEGER NOT NULL DEFAULT 0 CHECK (fragmentos >= 0),
        subido_por    INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        subido_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (subido_en IS datetime(subido_en)),
        restaurada_de INTEGER,      -- NULL = subida normal; N = copia de la version N
        UNIQUE (documento_id, numero)
    );

CREATE TABLE conversaciones (
        id             INTEGER PRIMARY KEY,
        usuario_id     INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        titulo         TEXT NOT NULL,
        iniciada_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (iniciada_en IS datetime(iniciada_en)),
        resumen        TEXT,
        resumen_hasta  INTEGER NOT NULL DEFAULT 0
    );

CREATE TABLE mensajes (
        id               INTEGER PRIMARY KEY,
        conversacion_id  INTEGER NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
        rol              TEXT NOT NULL CHECK (rol IN ('user', 'bot')),
        texto            TEXT NOT NULL,
        citas            TEXT,              -- JSON de citas (solo mensajes del bot)
        creado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (creado_en IS datetime(creado_en))
    );

CREATE TABLE consultas (
        id          INTEGER PRIMARY KEY,
        carrera_id  INTEGER NOT NULL REFERENCES carreras(id) ON DELETE CASCADE,
        curso_id    INTEGER REFERENCES cursos(id) ON DELETE SET NULL,
        usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        modo        TEXT NOT NULL CHECK (modo IN ('general', 'curso', 'ambos')),
        pregunta    TEXT NOT NULL,
        respondida  INTEGER NOT NULL CHECK (respondida IN (0, 1)),
        creado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (creado_en IS datetime(creado_en))
    );

CREATE TABLE logs (
        id          INTEGER PRIMARY KEY,
        usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        accion      TEXT NOT NULL,
        detalle     TEXT,
        creado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (creado_en IS datetime(creado_en))
    );

CREATE TABLE parametros (
        clave            TEXT PRIMARY KEY,
        valor            TEXT NOT NULL,
        tipo             TEXT NOT NULL CHECK (tipo IN ('entero', 'decimal', 'texto')),
        minimo           REAL,
        maximo           REAL,
        descripcion      TEXT NOT NULL,
        actualizado_por  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
        actualizado_en DATETIME NOT NULL DEFAULT (datetime('now','localtime')) CHECK (actualizado_en IS datetime(actualizado_en))
    );

CREATE UNIQUE INDEX ux_documento_ambito
        ON documentos (carrera_id, IFNULL(curso_id, 0), nombre);

CREATE INDEX ix_cursos_carrera ON cursos(carrera_id);

CREATE INDEX ix_curso_docente_usuario ON curso_docente(usuario_id);

CREATE INDEX ix_versiones_doc ON documento_versiones(documento_id);

CREATE INDEX ix_conv_usuario ON conversaciones(usuario_id);

CREATE INDEX ix_mensajes_conv ON mensajes(conversacion_id);

CREATE INDEX ix_consultas_carrera ON consultas(carrera_id, curso_id);

CREATE INDEX ix_logs_fecha ON logs(creado_en);

PRAGMA user_version = 5;
