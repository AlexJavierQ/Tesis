-- ESQUEMA v6: lo que se agrego al modelo v5 (referencia, NO es un script de migracion).
-- La fuente de verdad es nucleo/bd.py, que crea estos objetos y migra los datos
-- al arrancar (con respaldo previo en datos/respaldos/). Este archivo se genera
-- desde la base ya migrada para poder leer el SQL de un vistazo.
-- Requisitos: RF-06, RF-12, RF-15, RF-17, RF-21; RNF-04 y RNF-09.

-- ===== Tablas nuevas =====

CREATE TABLE citas_mensaje (
        id                    INTEGER PRIMARY KEY,
        mensaje_id            INTEGER NOT NULL REFERENCES mensajes(id) ON DELETE CASCADE,
        documento_version_id  INTEGER NOT NULL
                              REFERENCES documento_versiones(id) ON DELETE RESTRICT,
        pagina                INTEGER NOT NULL CHECK (pagina >= 1),
        seccion               TEXT NOT NULL DEFAULT '',
        UNIQUE (mensaje_id, documento_version_id, pagina, seccion)
    );

CREATE TABLE consulta_eventos (
        id            INTEGER PRIMARY KEY,
        carrera_id    INTEGER NOT NULL REFERENCES carreras(id) ON DELETE RESTRICT,
        curso_id      INTEGER REFERENCES cursos(id) ON DELETE SET NULL,
        modo          TEXT NOT NULL CHECK (modo IN ('general', 'curso', 'ambos')),
        categoria     TEXT NOT NULL CHECK (categoria IN ('horas', 'plazos', 'formatos', 'evaluacion', 'requisitos', 'tramites', 'otros')),
        con_respaldo  INTEGER NOT NULL CHECK (con_respaldo IN (0, 1)),
        origen        TEXT NOT NULL DEFAULT 'chat'
                      CHECK (origen IN ('chat', 'migracion', 'sintetico')),
        dia           DATE NOT NULL DEFAULT (date('now','localtime'))
                      CHECK (dia IS date(dia))
    );

-- ===== Indices =====

CREATE INDEX ix_citas_mensaje ON citas_mensaje(mensaje_id);

CREATE INDEX ix_citas_version ON citas_mensaje(documento_version_id);

CREATE INDEX ix_eventos_ambito ON consulta_eventos(carrera_id, curso_id, dia);

-- ===== Disparadores (reglas de integridad) =====

CREATE TRIGGER trg_consulta_eventos_curso_carrera_ins
    BEFORE INSERT ON consulta_eventos
    WHEN NEW.curso_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'El curso no pertenece a la carrera indicada.')
      WHERE NOT EXISTS (SELECT 1 FROM cursos
                        WHERE id = NEW.curso_id AND carrera_id = NEW.carrera_id);
    END;

CREATE TRIGGER trg_consulta_eventos_curso_carrera_upd
    BEFORE UPDATE OF carrera_id, curso_id ON consulta_eventos
    WHEN NEW.curso_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'El curso no pertenece a la carrera indicada.')
      WHERE NOT EXISTS (SELECT 1 FROM cursos
                        WHERE id = NEW.curso_id AND carrera_id = NEW.carrera_id);
    END;

CREATE TRIGGER trg_curso_docente_ins
    BEFORE INSERT ON curso_docente
    BEGIN
      SELECT RAISE(ABORT, 'Solo se asigna un docente de la carrera del curso.')
      WHERE NOT EXISTS (
        SELECT 1 FROM usuarios u
        JOIN roles r            ON r.id = u.rol_id
        JOIN usuario_carrera uc ON uc.usuario_id = u.id
        JOIN cursos cu          ON cu.carrera_id = uc.carrera_id
        WHERE u.id = NEW.usuario_id AND r.nombre = 'docente' AND cu.id = NEW.curso_id);
    END;

CREATE TRIGGER trg_documentos_curso_carrera_ins
    BEFORE INSERT ON documentos
    WHEN NEW.curso_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'El curso no pertenece a la carrera indicada.')
      WHERE NOT EXISTS (SELECT 1 FROM cursos
                        WHERE id = NEW.curso_id AND carrera_id = NEW.carrera_id);
    END;

CREATE TRIGGER trg_documentos_curso_carrera_upd
    BEFORE UPDATE OF carrera_id, curso_id ON documentos
    WHEN NEW.curso_id IS NOT NULL
    BEGIN
      SELECT RAISE(ABORT, 'El curso no pertenece a la carrera indicada.')
      WHERE NOT EXISTS (SELECT 1 FROM cursos
                        WHERE id = NEW.curso_id AND carrera_id = NEW.carrera_id);
    END;
