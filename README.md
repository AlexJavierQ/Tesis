# Asistente de Prácticum · UTPL

Asistente conversacional (RAG) que responde consultas de estudiantes sobre
prácticas preprofesionales **usando solo documentos oficiales**, cita de dónde
sale cada dato (archivo, página, sección y versión) y, si la respuesta no está
en los documentos, lo dice y deriva a la coordinación en lugar de inventar.

Trabajo de Integración Curricular, carrera de Computación, UTPL.

## Corpus oficial

| Documento | Ámbito | Vigencia registrada |
|---|---|---|
| Resolución Rectoral *Modelo de Prácticas Preprofesionales* (VAC_RR_2_2019_V3_2023) | Normativa general de Computación | Desde octubre 2023 – febrero 2024 |
| Capacitación *Prácticas Preprofesionales — Entorno Laboral*, versión en texto accesible | Curso Prácticum 2 | Período abril–agosto 2024 (fechas históricas) |

Los PDF están en `datos/docs/`. La vigencia se edita desde **Documentos** y el
asistente la menciona cuando cita fechas o plazos.

## Arquitectura

```
 React (Vite)             Widget JS embebible
        \                      /
         API REST (FastAPI)  ← único backend; valida permisos
                  |
          núcleo Python (nucleo/)
  rag · busqueda · memoria · ingest · pdfreader · llm · auth · bd · ...
        |                 |                    |
  SQLite (15 tablas)   ChromaDB (vectores)   PDFs en datos/docs/
                          |
                Groq (modelo openai/gpt-oss-20b)
```

Cómo responde una pregunta:

1. **Memoria:** si depende de lo conversado ("¿y quién lo evalúa?"), el modelo la
   reescribe para que se entienda sola.
2. **Búsqueda híbrida:** combina búsqueda por significado (vectores) y por palabras
   clave (BM25) dentro del ámbito elegido (normativa general, el curso, o ambos).
3. **Umbral anti-alucinación:** si nada se parece lo suficiente, se abstiene sin
   llamar al modelo.
4. **Secciones completas:** se indexan fragmentos cortos, pero el modelo lee la
   sección entera de donde salen, con su título y su vigencia.
5. **Respuesta y citas:** solo con ese contexto. Las citas guardan documento y
   versión, y se ordenan según cuánto respaldan lo que se respondió.

## Puesta en marcha

```bash
python -m venv venv
venv\Scripts\activate                 # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy secretos.toml.example secretos.toml   # y pon tu GROQ_API_KEY
python arrancar.py
```

`arrancar.py` indexa los PDF si hace falta, revisa que el índice coincida con
el catálogo, levanta la API (puerto 8000) y React (puerto 5173). En una
instalación nueva registra los PDF de `datos/docs/` con la vigencia indicada en
`datos/docs/vigencias.json`. Requiere Node.js para React, y la primera vez
descarga el modelo de embeddings (~470 MB), así que necesita internet.

**Primer acceso:** si la base de datos no tiene usuarios, se crea `admin`. Su
contraseña es `ADMIN_PASSWORD` (en `secretos.toml`) o, si no la defines, una al
azar que se muestra una sola vez en la consola. Desde **Usuarios** el
administrador crea a la coordinación y le asigna sus carreras.

Para pruebas locales existe `python -m nucleo.auth --prueba`, que crea cuentas
de prueba con contraseña conocida. **No lo uses en un servidor real.**

## Roles

| Rol | Gestiona |
|---|---|
| Administrador | Facultades y carreras, todos los usuarios, configuración del sistema, registro de actividad |
| Coordinación | En sus carreras: documentos generales, cursos, asignación de docentes, estudiantes y docentes, métricas |
| Docente | Documentos y métricas de los cursos que tiene asignados |
| Estudiante | Chat con historial |

## Verificar

```bash
python verificar.py              # prueba de humo (9 pasos, sin cuentas de prueba)
python -m pruebas.integridad     # permisos, versionado, trazabilidad y fallos
python revisar_pdf.py <archivo>  # revisa si un PDF es apto antes de subirlo
```

## Estructura

```
nucleo/          motor: rag, busqueda, memoria, ingest, pdfreader, llm, bd, auth, ...
interfaces/      api.py (FastAPI), react/ (aplicación web), widget/ (chat embebible)
datos/docs/      corpus oficial en PDF (sistema.db y chroma_db se generan)
pruebas/         pruebas automáticas de integridad
evaluacion/      evaluación del sistema (historico/ = pruebas con el corpus de demo)
documentacion/   diseño, base de datos, anti-alucinación, formato de documentos
```

Documentación principal: [arquitectura](documentacion/DISENO_ARQUITECTURA.md),
[base de datos](documentacion/DISENO_BD.md),
[formato de documentos](documentacion/FORMATO_DOCUMENTOS.md),
[resumen técnico](documentacion/RESUMEN_PARA_REVISION.md).
