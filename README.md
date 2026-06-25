# Asistente de Prácticum — MVP (RAG)

Plataforma web que responde consultas sobre Prácticum usando solo los documentos
oficiales como fuente, citando de dónde sale cada respuesta y sin inventar.

Arquitectura modular (cada herramienta aislada en su adaptador):

| Capa | Archivo | Herramienta |
|---|---|---|
| Embeddings | `embeddings.py` | Sentence-Transformers (MiniLM) |
| Base vectorial | `vectorstore.py` | ChromaDB |
| LLM | `llm.py` | Groq (Llama) / Gemini |
| Lector PDF | `pdfreader.py` | PyMuPDF |
| Orquestador | `rag.py` | — |
| Ingesta | `ingest.py` | — |
| Interfaz web | `app.py` | Streamlit |
| API REST | `api.py` | FastAPI |

## Cómo correrlo (comandos mínimos)

```bash
git clone https://github.com/AlexJavierQ/Tesis.git
cd Tesis

python -m venv venv
venv\Scripts\activate            # Windows   (Linux/Mac: source venv/bin/activate)

pip install -r requirements.txt

# 1) configurar la key del LLM
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
#   abre ese archivo y pon tu GROQ_API_KEY (gratis en https://console.groq.com/keys)

# 2) crear un reglamento de demo e indexarlo
python make_demo_pdf.py
python ingest.py

# 3) levantar la app
streamlit run app.py
```

Se abre en el navegador. En la barra lateral eliges el rol:

- **Estudiante** — chat. Pregunta y recibe respuestas citadas.
- **Docente** (clave demo `docente2026`) — crea cursos y sube documentos a su curso.
- **Coordinación** (clave demo `utpl2026`) — sube reglamentos globales y ve métricas.

## API REST (opcional)

La misma lógica expuesta por HTTP, para que cualquier frontend la consuma:

```bash
uvicorn api:app --reload
# docs interactivas:  http://localhost:8000/docs
```

## Cómo cambiar de modelo de lenguaje

Solo se edita `secrets.toml` (no el código):

```toml
LLM_PROVIDER = "groq"     # 14.400 req/día gratis (Llama 3.1 8B)
# o
LLM_PROVIDER = "gemini"   # requiere GEMINI_API_KEY real (AIza...)
```

## Validar las herramientas

```bash
python pruebas_herramientas.py
```
Compara embeddings (MiniLM vs e5), lector de PDF (PyMuPDF vs pypdf), tamaño de
chunk y latencia. Ver `RESULTADOS_PRUEBAS.md` y `ALTERNATIVAS_LLM.md`.

## Notas

- Sin key, la app igual recupera y muestra los fragmentos oficiales (degrada con elegancia).
- Anti-alucinación: si ningún fragmento se parece lo suficiente, no inventa y deriva a la coordinación.
- Las métricas son anónimas (solo el texto de la consulta y la fecha, nunca quién preguntó).
- Es un MVP: prioriza demostrar el flujo completo, no la robustez de producción.
