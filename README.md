# Asistente de Prácticum

Chatbot que responde consultas sobre el Prácticum de Computación (UTPL)
**usando solo los documentos oficiales** como fuente, y citando de dónde
salió cada respuesta.

Si el reglamento no lo dice, se abstiene y deriva a coordinación. No inventa.

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend                       │  React + Vite  │  Widget   │
├─────────────────────────────────┴──────┬─────────┴───────────┤
│  API REST (FastAPI)                     │  ← ambos hablan     │
│                                         │    por HTTP con esta│
├─────────────────────────────────────────┴────────────────────┤
│  Núcleo RAG (Python)   [rag / ingest / vectorstore / llm /   │
│                         embeddings / auth / metricas]         │
├───────────────────────────────────────────────────────────────┤
│  ChromaDB (vectores)  · SQLite (login + métricas)  · PDFs    │
└───────────────────────────────────────────────────────────────┘
```

## Puesta en marcha (un solo comando)

```bash
python -m venv venv
venv\Scripts\activate                # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# crea .streamlit/secrets.toml con tu GROQ_API_KEY (gratis en console.groq.com/keys)

python arrancar.py
```

`arrancar.py` hace todo: genera el corpus de demo si falta, indexa los
PDF si falta, siembra los usuarios demo, levanta la API en el puerto
8000 y React en el puerto 5173.

Abre <http://localhost:5173> y entra con `estudiante`/`demo2026`.

## Usuarios de demostración

| Usuario     | Contraseña  | Rol           |
|-------------|-------------|---------------|
| `estudiante` | `demo2026` | estudiante    |
| `docente`    | `demo2026` | docente       |
| `coord`      | `demo2026` | coordinación  |

Se crean automáticamente la primera vez que arranca el sistema.

## Roles y permisos

| Acción                        | Estudiante | Docente | Coordinación |
|-------------------------------|:---:|:---:|:---:|
| Consultar en el chat          | ✓ | ✓ | ✓ |
| Ver documentos                | ✓ | ✓ | ✓ |
| Subir documentos a un curso   |   | ✓ | ✓ |
| Subir reglamentos generales   |   |   | ✓ |
| Ver métricas de un curso      |   | ✓ | ✓ |
| Ver métricas de toda la carrera |   |   | ✓ |

El widget (`interfaces/widget/`) es **público** (sin login), pensado
para integrarse en el portal universitario donde el estudiante ya está.

## Otras utilidades

- `python verificar.py` — smoke test del backend (~15 s, sin GUI).
- `python revisar_pdf.py <ruta.pdf>` — valida si un PDF cumple los
  lineamientos antes de subirlo.

## Documentación

- [Alcances del sistema](documentacion/ALCANCES.md) — qué está dentro y
  qué queda fuera, con justificación. **Léelo antes de la sustentación.**
- [Formato de los documentos](documentacion/FORMATO_DOCUMENTOS.md) —
  lineamientos que deben cumplir los PDFs que se suban al sistema.
- [Guía de aprendizaje](documentacion/GUIA_APRENDIZAJE.md) — cada archivo
  explicado línea por línea. **Empieza aquí para estudiar el código.**
- [Diseño de base de datos](documentacion/DISENO_BD.md) — diagramas ER.
- [Diseño de arquitectura](documentacion/DISENO_ARQUITECTURA.md) —
  diagramas C4, flujos, secuencia.
- [Anti-alucinación](documentacion/ANTIALUCINACION.md) — experimentos.
- [Evaluación del sistema](documentacion/EVALUACION_SISTEMA.md) —
  métricas sobre el corpus.
- [Frontends](documentacion/FRONTENDS.md) — comparación de las interfaces.

## Estructura del proyecto

```
mvp_practicum/
├── arrancar.py                    UN comando para arrancar todo
├── verificar.py                   smoke test (opcional)
├── revisar_pdf.py                 valida PDFs (opcional)
├── nucleo/                        motor RAG y adaptadores
│   ├── config.py                  carga la API key
│   ├── pdfreader.py               lee PDFs (PyMuPDF)
│   ├── embeddings.py              MiniLM multilingüe
│   ├── vectorstore.py             ChromaDB
│   ├── llm.py                     Groq (gpt-oss-20b)
│   ├── ingest.py                  procesa PDFs -> chunks -> índice
│   ├── rag.py                     orquestador
│   ├── auth.py                    login (usuarios + sesiones)
│   └── metricas.py                registro anónimo
├── interfaces/
│   ├── api.py                     FastAPI (backend único)
│   ├── react/                     React + Vite (frontend principal)
│   └── widget/                    widget JS puro embebible
├── evaluacion/
│   ├── preguntas_eval.json        85 preguntas etiquetadas
│   ├── evaluacion.py              corre el banco, genera informe
│   └── pruebas_herramientas.py    valida decisiones técnicas
├── documentacion/                 guías para leer y defender el sistema
└── datos/                         (no versionado)
    ├── docs/                      corpus PDF
    ├── chroma_db/                 índice vectorial
    ├── consultas.db               métricas
    └── usuarios.db                login
```

## Notas

- **Modo degradado:** si no hay `GROQ_API_KEY`, el sistema sigue
  recuperando fragmentos y los muestra crudos, en vez de romperse.
- **Métricas anónimas:** se guarda el texto de la pregunta y la fecha,
  nunca quién preguntó.
- **Sistema piloto:** para pasar a producción abierta hace falta HTTPS,
  backup de las BD, contraseñas rotadas, y CORS restringido a los dominios
  reales. Ver [ALCANCES.md](documentacion/ALCANCES.md) §3.7.
