# Evaluaciones históricas (corpus de demostración)

Todo lo de esta carpeta se hizo **antes de usar documentos oficiales**, sobre un
corpus de demostración (un reglamento ficticio y una presentación con la mitad
de páginas solo en imagen). Se conserva como evidencia del proceso de diseño de
la tesis, no como resultado final.

| Archivo | Qué fue | Para qué sirvió |
|---|---|---|
| `pruebas_herramientas.py` | Comparación PyMuPDF vs pypdf, MiniLM vs e5, tamaños de fragmento (6 preguntas) | Elegir las herramientas del prototipo |
| `evaluacion.py`, `preguntas_eval.json` | 85 preguntas sobre el corpus ficticio | Calibrar el umbral anti-alucinación |
| `medir_memoria.py`, `resultados_memoria*.md/json` | Concatenación vs resumen + reescritura (2 conversaciones) | Decidir la estrategia de memoria conversacional |

**Limitaciones:** las preguntas y el corpus los escribió la misma persona, la
muestra es pequeña y el corpus no es oficial. Los scripts usan rutas y datos de
ese corpus, así que no están pensados para volver a ejecutarse. La evaluación
final (RAGAS y prueba con estudiantes) se hace sobre los documentos oficiales.
