-- PROPUESTA V1 (10/11/2026). NO EJECUTAR EN PRODUCCION SIN RESPALDO Y PRUEBAS.
-- Complementa el esquema actual v5 de nucleo/bd.py, no lo sustituye.
-- No modifica user_version: la migracion definitiva requiere integracion en bd.py.
-- Requisitos: RF-06, RF-12, RF-21; RNF-04 y RNF-09.

BEGIN IMMEDIATE;

-- Citas normalizadas: vinculo estable mensaje -> version exacta del PDF.
-- El campo mensajes.citas (JSON) se conserva transitoriamente por compatibilidad.
CREATE TABLE IF NOT EXISTS citas_mensaje (
    id INTEGER PRIMARY KEY,
    mensaje_id INTEGER NOT NULL REFERENCES mensajes(id) ON DELETE CASCADE,
    documento_version_id INTEGER NOT NULL
        REFERENCES documento_versiones(id) ON DELETE RESTRICT,
    pagina INTEGER NOT NULL CHECK (pagina >= 1),
    seccion TEXT NOT NULL DEFAULT '',
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (mensaje_id, documento_version_id, pagina, seccion)
);
CREATE INDEX IF NOT EXISTS ix_citas_mensaje
    ON citas_mensaje(mensaje_id);
CREATE INDEX IF NOT EXISTS ix_citas_version
    ON citas_mensaje(documento_version_id);

-- Eventos analiticos: categorias controladas, sin pregunta literal, usuario ni IP.
-- La tabla antigua consultas permanece como LEGACY hasta aprobar retencion.
CREATE TABLE IF NOT EXISTS consulta_eventos (
    id INTEGER PRIMARY KEY,
    carrera_id INTEGER NOT NULL REFERENCES carreras(id) ON DELETE RESTRICT,
    curso_id INTEGER REFERENCES cursos(id) ON DELETE SET NULL,
    modo TEXT NOT NULL CHECK (modo IN ('general', 'curso', 'ambos')),
    categoria TEXT NOT NULL CHECK (categoria IN (
        'horas', 'plazos', 'formatos', 'evaluacion',
        'requisitos', 'tramites', 'otros'
    )),
    con_respaldo INTEGER NOT NULL CHECK (con_respaldo IN (0,1)),
    creado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_eventos_ambito_fecha
    ON consulta_eventos(carrera_id, curso_id, creado_en);
CREATE INDEX IF NOT EXISTS ix_eventos_categoria
    ON consulta_eventos(categoria, con_respaldo);

-- Un curso no puede asociarse a una carrera distinta en el registro de eventos.
CREATE TRIGGER IF NOT EXISTS trg_eventos_curso_carrera_ins
BEFORE INSERT ON consulta_eventos
WHEN NEW.curso_id IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'Curso no pertenece a la carrera')
  WHERE NOT EXISTS (
    SELECT 1 FROM cursos
    WHERE id = NEW.curso_id AND carrera_id = NEW.carrera_id
  );
END;
CREATE TRIGGER IF NOT EXISTS trg_eventos_curso_carrera_upd
BEFORE UPDATE OF carrera_id, curso_id ON consulta_eventos
WHEN NEW.curso_id IS NOT NULL
BEGIN
  SELECT RAISE(ABORT, 'Curso no pertenece a la carrera')
  WHERE NOT EXISTS (
    SELECT 1 FROM cursos
    WHERE id = NEW.curso_id AND carrera_id = NEW.carrera_id
  );
END;

COMMIT;
