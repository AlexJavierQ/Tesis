# Asistente de Prácticum — MVP (RAG)

Plataforma web que responde consultas sobre Prácticum usando solo los documentos
oficiales como fuente, citando de dónde sale cada respuesta y sin inventar.

## Arquitectura

El backend Python expone una **API REST** y el frontend la consume por HTTP. Esa
separación es la que permite cambiar de interfaz sin tocar el núcleo (propuesta 2
del anexo de frontend: React consume la API, el motor RAG se queda en Python).

| Capa | Archivo | Herramienta |
|---|---|---|
| Embeddings | `nucleo/embeddings.py` | Sentence-Transformers (MiniLM multilingüe) |
| Base vectorial | `nucleo/vectorstore.py` | ChromaDB |
| LLM | `nucleo/llm.py` | Groq (Llama 3.1) / Gemini |
| Lector PDF | `nucleo/pdfreader.py` | PyMuPDF |
| Orquestador RAG | `nucleo/rag.py` | orquestación propia, sin framework |
| Ingesta | `nucleo/ingest.py` | — |
| Métricas y registro | `nucleo/metricas.py` | SQLite |
| Configuración | `nucleo/config.py` | — |
| API REST | `interfaces/api.py` | FastAPI |
| Interfaz web | `interfaces/react/` | React + Vite |
| Widget embebible | `interfaces/widget/` | JavaScript (sin build) |
| Interfaz de respaldo | `interfaces/streamlit/streamlit_app.py` | Streamlit |

Cada herramienta vive aislada en su adaptador: cambiar una es reimplementar un
archivo, no tocar el sistema. Eso es lo que hace reproducibles las comparativas
de `evaluacion/pruebas_herramientas.py`.

## Estructura del proyecto

```
mvp_practicum/
  nucleo/          motor RAG y adaptadores (rag, embeddings, vectorstore, llm, pdfreader, ingest, config, metricas)
  interfaces/      api.py + los tres frontends (react/, widget/, streamlit/)
  evaluacion/      banco de pruebas y evaluación del sistema
  datos/           docs/ (corpus), chroma_db/ (índice), consultas.db (métricas)
  documentacion/   notas técnicas y resultados
  make_demo_pdf.py, seed_consultas.py   scripts de datos de demostración
```

El núcleo no conoce a las interfaces: expone su lógica y cualquier frontend la
consume por la API. Por eso hay tres interfaces sobre el mismo motor.

> **Nota:** la orquestación es propia, no usa LangChain. Es una decisión
> deliberada: el flujo (recuperar → filtrar por umbral → construir prompt →
> generar → verificar) cabe en `rag.py` y mantenerlo explícito es lo que permite
> intercambiar embeddings, base vectorial o LLM de forma independiente.

## Parámetros del motor

Valores efectivos, para que coincidan con lo documentado en el Cap. 3:

| Parámetro | Valor | Dónde |
|---|---|---|
| Fragmentos recuperados (top-k) | 8 | `rag.TOP_K` |
| Umbral de distancia coseno | 0.65 | `rag.THRESHOLD` |
| Citas mostradas al usuario | 3 | `rag.MAX_CITAS` |
| Segmentación | por unidad normativa (artículo/título/párrafo) | `ingest.bloques_semanticos` |
| Tamaño máximo de fragmento | 500 caracteres | `ingest.CHUNK_SIZE` |
| Solapamiento (solo al partir un bloque largo) | 80 caracteres | `ingest.OVERLAP` |
| Temperatura de generación | 0.2 | `llm.TEMPERATURA` |
| Temperatura de verificación | 0.0 | `llm.TEMPERATURA_JUICIO` |
| Métrica de similitud | coseno | `vectorstore.get_collection` |
| Modelo de embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | `embeddings.MODEL_NAME` |

Los valores de top-k y de segmentación salen de barridos medidos; el detalle
está en `documentacion/ANTIALUCINACION.md`.

## Puesta en marcha

### 1. Backend

```bash
python -m venv venv
venv\Scripts\activate              # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

copy .streamlit\secrets.toml.example .streamlit\secrets.toml
#   abre ese archivo y pon tu GROQ_API_KEY (gratis en https://console.groq.com/keys)

python make_demo_pdf.py                # genera el corpus de desarrollo en datos/docs
python -m nucleo.ingest                # indexa los PDF
uvicorn interfaces.api:app --reload    # queda en http://localhost:8000
```

Documentación interactiva de la API: <http://localhost:8000/docs>

### 2. Frontend

```bash
cd interfaces/react
npm install
npm run dev                        # queda en http://localhost:5173
```

Si la API no corre en el puerto por defecto, copia `interfaces/react/.env.example` como
`interfaces/react/.env.local` y ajusta `VITE_API_URL`.

## Roles

Se eligen desde el panel lateral. **Todavía sin autenticación** — es lo siguiente
en la lista, y hasta que exista no debe exponerse fuera de la red local.

- **Estudiante** — chat con citas clicables que abren el PDF en la página exacta.
- **Docente** — crea cursos y sube documentos que solo afectan al chat de su curso.
- **Coordinación** — sube reglamentos de la carrera y ve las métricas agregadas.

## Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/salud` | Estado, proveedor de LLM activo y nº de fragmentos indexados |
| GET | `/carreras` · `/carreras/{c}/cursos` | Estructura del corpus |
| POST | `/carreras/{c}/cursos` | Crear curso |
| POST | `/preguntar` | Consulta → respuesta + citas |
| GET · POST · DELETE | `/documentos` | Listar, subir e indexar, eliminar |
| GET | `/documentos/pagina` | PNG de una página (visor de citas) |
| GET | `/documentos/info` | Nº de páginas de un documento |
| GET | `/metricas` | Agregado anónimo, filtrable por carrera y curso |

## Cambiar de modelo de lenguaje

Solo se edita `secrets.toml`, no el código:

```toml
LLM_PROVIDER = "groq"     # por defecto. 14.400 req/día gratis (Llama 3.1 8B)
# o
LLM_PROVIDER = "gemini"   # requiere GEMINI_API_KEY real (AIza...)
```

## Validar las herramientas

```bash
python evaluacion/pruebas_herramientas.py
```

Compara embeddings (MiniLM vs e5), lector de PDF (PyMuPDF vs pypdf), tamaño de
chunk y latencia. Resultados en `documentacion/RESULTADOS_PRUEBAS.md`.

> **Limitación conocida:** ese banco evalúa 6 preguntas sobre un PDF de demostración
> generado por `make_demo_pdf.py`. Sirve para elegir entre herramientas, **no** es
> la evaluación del sistema. La evaluación formal con RAGAS y SUS sobre los
> reglamentos reales está pendiente.

## Notas

- Sin API key la app sigue recuperando y mostrando los fragmentos oficiales
  (degrada con elegancia en lugar de romperse).
- Anti-alucinación por capas: (1) umbral de similitud antes de llamar al LLM,
  (2) prompt restrictivo, (3) cita literal verificada mecánicamente —la respuesta
  debe aportar una frase real del contexto, comprobada por comparación de cadenas—
  y (4) citación obligatoria de la fuente. Qué aporta cada capa, medido:
  `documentacion/ANTIALUCINACION.md`.
- Las métricas son anónimas: se guarda el texto de la consulta y la fecha, nunca
  quién preguntó.
- `seed_consultas.py` inserta consultas **de demostración**, no de uso real.
  Cualquier métrica mostrada tras ejecutarlo debe etiquetarse como tal.
- Es un MVP: prioriza demostrar el flujo completo, no la robustez de producción.
