# Asistente de Prácticum UTPL: resumen técnico para revisión externa

> Documento pensado para que otra persona o IA revise el proyecto y dé su
> perspectiva. Describe el estado **actual** del sistema (octubre 2026).
> Al final hay preguntas concretas sobre las que me interesa una opinión.

## 1. Contexto

**Trabajo de Integración Curricular (TIC)**, carrera de Computación, UTPL (Ecuador).

**Título:** Implementación de un Agente Inteligente para la Asistencia Estudiantil
y Análisis de Consultas sobre Prácticas Preprofesionales.

**Objetivo general:** desarrollar una plataforma web basada en
Retrieval-Augmented Generation (RAG) que asista las consultas de los estudiantes
de Prácticum sobre prácticas preprofesionales, complementada con un módulo de
análisis de patrones de consulta para apoyar a la coordinación docente.

| Objetivo específico | Estado |
|---|---|
| OE1. Estado del arte y arquitectura | Hecho |
| OE2. Pipeline de ingesta y motor RAG | Hecho |
| OE3. Interfaces web (chat y panel analítico) | Hecho |
| OE4. Evaluación (RAGAS para calidad, SUS para usabilidad con estudiantes reales) | Pendiente |

El problema que resuelve: los estudiantes preguntan siempre lo mismo (horas,
plazos, formatos, notas, trámites) y la información está dispersa en
reglamentos y presentaciones. El asistente responde **solo** con los documentos
oficiales, cita la fuente (archivo y página) y, si el dato no está, lo dice y
deriva a la coordinación en vez de inventar.

## 2. Arquitectura

```
 React (Vite)          Widget JS (Shadow DOM,        ← interfaces
 chat + panel          embebible en el portal)
        \                    /
         FastAPI (interfaces/api.py)   ← único backend, valida permisos
                    |
              núcleo Python (nucleo/)
   rag · memoria · ingest · llm · auth · historial · metricas · parametros · bd
        |                 |                     |
  SQLite (sistema.db)  ChromaDB (vectores)   PDFs en datos/docs/
  15 tablas            fragmentos + embeddings
                          |
                  Groq API (LLM: openai/gpt-oss-20b)
```

- **El núcleo no sabe nada de la web**: la API solo orquesta, valida y serializa.
- **Dos almacenes**: SQLite es la fuente de verdad (estructura, usuarios,
  documentos, chat, analítica, configuración); ChromaDB guarda los vectores. Se
  enlazan por la ruta del archivo.
- Un solo comando (`python arrancar.py`) indexa si hace falta y levanta la API y React.

### Stack

| Pieza | Tecnología | Motivo |
|---|---|---|
| Lenguaje backend | Python 3.11+ | ecosistema de IA |
| API | FastAPI + Pydantic | validación declarativa, documentación automática |
| Frontend | React 19 + Vite | componentes, rápido de desarrollar |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, local) | multilingüe, gratis, corre en CPU |
| Base vectorial | ChromaDB (distancia coseno) | embebida, sin servidor |
| Base relacional | SQLite | sin servidor, suficiente para el alcance |
| Lectura de PDF | PyMuPDF | texto por página, renderiza páginas para el visor |
| LLM | Groq, `openai/gpt-oss-20b`, temperatura 0.2 | gratis, rápido, buena fidelidad al contexto |

## 3. Motor RAG (nucleo/rag.py)

**Ingesta:** cada PDF se lee por página, se trocea en fragmentos de 500
caracteres con 80 de solape y se guarda en ChromaDB con metadatos
`{fuente, pagina, scope, path}`. `scope` es `carrera|global` (reglamentos de
la carrera) o `carrera|curso:X` (material de un curso).

**Respuesta a una pregunta:**

1. **Capa social:** saludos, "gracias" y "ayuda" se responden sin buscar ni llamar al modelo.
2. **Memoria:** la pregunta se reescribe para que se entienda sola (sección 4).
3. **Recuperación:** búsqueda semántica (top-k = 8) filtrada por ámbito. El
   estudiante elige desde dónde quiere la respuesta:
   - `general`: solo los reglamentos de la carrera;
   - `curso`: solo el material del curso;
   - `ambos`: dos búsquedas separadas.
4. **Capa anti-alucinación 1 (umbral):** se descartan los fragmentos con
   distancia > 0.65. Si no queda ninguno, el sistema se abstiene **sin llamar al modelo**.
5. **Capa 2 (prompt restrictivo):** "responde SOLO con el contexto; si no está,
   responde EXACTAMENTE esta frase". Si el modelo devuelve la frase, se marca como
   respuesta sin respaldo y se ocultan las citas.
6. **Modo `ambos`:** si las dos búsquedas aportan, un prompt doble pide separar
   "En general: … / En Prácticum 2: …". Ejemplo real: el reglamento dice 120 h
   y la guía del curso dice 144 h; la respuesta muestra las dos con su fuente.
7. **Capa 3 (citas):** hasta 3 citas (archivo y página), mezclando las dos fuentes en modo `ambos`.
8. **Modo degradado:** si el modelo falla o no hay clave de API, se muestran los
   fragmentos recuperados tal cual (el sistema nunca queda sin responder).

## 4. Memoria conversacional (nucleo/memoria.py)

Problema: "¿y cuántas son del Prácticum 2?" o "¿quién lo evalúa?" no tienen tema
si se buscan solas.

Hay dos estrategias, elegibles por el administrador (parámetro `memoria_modo`):

| | Concatenación (original) | Resumen + reescritura (actual) |
|---|---|---|
| Qué hace | si la pregunta parece seguimiento (regla: ≤ 3 palabras, empieza con "y/pero/entonces", usa "eso/esa…"), le pega delante la pregunta anterior del estudiante | arma un contexto con la **ventana** (últimos 6 mensajes completos) y un **resumen** de todo lo anterior; con eso el modelo **reescribe** la pregunta para que sea autónoma |
| Llamadas extra al modelo | 0 | 1 por turno (reescritura) + 1 ocasional (resumen) |
| Alcance | 1 turno atrás, depende de la regla | toda la conversación |

Detalles de diseño:

- **El resumen es incremental**: se guarda en `conversaciones.resumen` junto con
  `resumen_hasta` (id del último mensaje incluido). Solo se recalcula cuando un
  mensaje sale de la ventana, no en cada pregunta.
- **La memoria sirve para entender la pregunta, nunca como fuente de la respuesta.**
  El prompt de respuesta recibe solo la pregunta reescrita y los fragmentos de
  los documentos. El resumen tiene orden explícita de **no copiar cifras ni reglas**
  de respuestas anteriores (se vuelven a buscar en los documentos); solo guarda
  los temas consultados y los datos que el estudiante dio de sí mismo.
- Las tareas auxiliares (reescribir y resumir) se piden al modelo con
  `reasoning_effort = low` para gastar menos.
- **Plan B:** si la reescritura falla, se vuelve a la concatenación.
- **Transparencia:** el chat muestra "Entendí tu pregunta como: …" cuando la reescribe.

**Decisión: no se implementaron "notas importantes" persistentes** (una memoria
aparte que el modelo llenaría con datos clave). Motivo: el modelo tendría que
decidir qué es importante, y si guarda un dato equivocado (por ejemplo una cifra
mal respondida), el error se repetiría en todas las respuestas siguientes. En su
lugar, el resumen tiene una sección fija "Datos del estudiante" con solo lo que
el estudiante dijo de sí mismo, y se reconstruye a partir de los mensajes reales.

### Medición del costo (evaluacion/medir_memoria.py)

Las dos estrategias se probaron sobre las mismas 2 conversaciones guionadas de
7 turnos cada una. Una de ellas tiene una referencia lejana: "volviendo a lo
primero, ¿esa figura recibe algún pago?". Las respuestas usan el modo `ambos`.
Se midieron los tokens que reporta Groq y el tiempo de cada turno sin contar las
esperas por límite de peticiones. El acierto se cuenta si la respuesta contiene
el dato esperado (palabra clave).

| Estrategia | Llamadas al modelo por turno | Tokens por turno | Tiempo por turno (mediana) | Aciertos |
|---|---|---|---|---|
| Concatenación (original) | 1,00 | 1.902 | 1,37 s | 10/13 (77 %) |
| Resumen + reescritura | 2,29 | 2.537 (**+33 %**) | 2,41 s (**+1,0 s**) | **13/13 (100 %)** |

Desglose de la estrategia nueva por tipo de llamada: reescritura ≈ 718 tokens y
0,8 s; resumen ≈ 571 tokens y 0,8 s (solo cuando un mensaje sale de la ventana);
respuesta ≈ 1.678 tokens y 1,9 s.

Qué falla con la concatenación: "¿quién **lo** evalúa?" se pega a la pregunta
anterior, que era sobre el formato, y no al informe. Y la referencia lejana se
pega al turno inmediatamente anterior, que hablaba de otra cosa. La reescritura
resolvió ambos casos.

Iteración del prompt: la **primera versión** del prompt de reescritura dejaba sin
completar preguntas que empezaban con "¿Y…?" (el modelo creía que ya se entendían
solas), convertía comentarios en preguntas y agregaba detalles que el estudiante
no pidió. Se corrigió con reglas explícitas y 3 ejemplos de **otros temas**, para
no ajustarlo a las preguntas de la prueba. Ambas corridas están en `evaluacion/`.

Cautelas:
- La muestra es pequeña (13 turnos evaluables).
- El acierto por palabra clave es aproximado: no es RAGAS.
- Hay picos aislados de latencia de Groq (hasta 9,6 s), por eso se reporta la mediana.

**Hallazgo práctico:** el plan gratuito de Groq tiene un tope de **200.000 tokens
al día** para todo el sistema, y la segunda repetición de la medición lo agotó.
Con estas cifras alcanza para unas 105 preguntas al día con concatenación y unas
79 con resumen. Para un piloto real hace falta un plan de pago u otro proveedor.
Cuando se agota la cuota, el sistema no se cae: la reescritura vuelve a la
concatenación y la respuesta pasa a modo degradado (muestra los fragmentos).

## 5. Modelo de datos (SQLite, 15 tablas, esquema v4)

| Grupo | Tablas |
|---|---|
| Estructura académica | `facultades` → `carreras` → `cursos`; `curso_docente` (N:M, qué docentes dictan cada curso) |
| Usuarios y acceso | `roles`, `usuarios` (con correo único y estado activo), `usuario_carrera` (N:M), `sesiones` (con expiración) |
| Documentos | `documentos` (`curso_id` NULL = global, estado activo/inactivo), `documento_versiones` (historial; `restaurada_de`) |
| Chat | `conversaciones` (con el resumen de la memoria), `mensajes` |
| Analítica y auditoría | `consultas` (relacionada con carrera, curso y usuario; modo de respuesta), `logs` (bitácora) |
| Configuración | `parametros` (valores editables desde la interfaz) |

Reglas de robustez:
- Fechas `DATETIME` con valor por defecto y `CHECK (x IS datetime(x))`.
- `CHECK` en valores cerrados y en el formato del correo.
- Claves foráneas activadas en cada conexión, con `ON DELETE` pensado tabla por
  tabla: `CASCADE` en hijos que no tienen sentido solos, `SET NULL` en registros
  históricos, `RESTRICT` donde borrar dejaría datos incoherentes.
- Índice único con `IFNULL(curso_id, 0)`, porque en SQLite dos NULL no chocan.
- Toda operación corre en una transacción (`commit` o `rollback`).
- La versión del esquema está en `PRAGMA user_version`, con migraciones automáticas sin pérdida de datos.

**Versionado de documentos:** subir un PDF con el mismo nombre crea la versión
siguiente; la anterior se archiva en `_versiones/`. Solo la vigente está indexada.
"Restaurar" funciona como `git revert`: crea una versión **nueva** con el contenido
de la elegida, sin borrar ni reescribir el historial. Desactivar un documento lo
quita de ChromaDB sin borrarlo.

## 6. Roles y permisos

| Rol | Puede | No puede |
|---|---|---|
| Administrador | configurar parámetros del sistema; gestionar todos los usuarios; ver la bitácora | gestionar contenido académico |
| Coordinación | crear facultades, carreras y cursos; asignar docentes a cursos; subir reglamentos generales; gestionar estudiantes y docentes de sus carreras; ver métricas de la carrera | tocar la configuración; crear coordinadores o administradores |
| Docente | subir, versionar, restaurar y activar/desactivar documentos **de sus cursos asignados**; ver sus métricas | crear cursos; subir reglamentos generales |
| Estudiante | chat con historial persistente | — |

Los permisos se validan en la API, endpoint por endpoint. El frontend solo
oculta lo que no corresponde.

**Parámetros configurables (sin tocar código):** umbral de similitud, top-k,
máximo de citas, modelo de IA, temperatura, umbral de agrupación de temas,
horas de sesión, tamaño máximo de PDF, mensajes fijos del bot, modo y ventana
de memoria. Cada valor se valida por tipo y rango y cada cambio queda en la
bitácora. La clave de API **no** es un parámetro: se queda fuera de la base de datos.

## 7. Seguridad

- Contraseñas con PBKDF2-HMAC-SHA256, 200.000 iteraciones, sal aleatoria y comparación en tiempo constante.
- Tokens de sesión opacos (32 bytes aleatorios) guardados en la base, con
  expiración configurable. Desactivar a un usuario o cambiar su contraseña cierra sus sesiones.
- Login con usuario o correo. Los intentos fallidos quedan en la bitácora.
- Protección contra rutas manipuladas (`../`) al servir PDFs; validación de que el archivo sea PDF y de su tamaño.
- CORS limitado a los orígenes conocidos; la clave de API en `secrets.toml`, ignorado por git.

## 8. Analítica para la coordinación

- Total de consultas, porcentaje con respaldo documental, preguntas sin respaldo
  (muestran qué falta en los documentos).
- **Temas más consultados agrupados por significado:** las preguntas se
  convierten en vectores y se agrupan por similitud coseno ≥ 0.70 (enlace
  simple, voraz). Así "¿cuántas horas necesito?" y "¿cuál es el total de horas?"
  cuentan como un solo tema.
- Nunca se muestra quién preguntó qué.

## 9. Lo verificado hasta ahora

- `verificar.py`: 9 pasos (importaciones, clave, índice, login, recuperación,
  abstención fuera de dominio, respuesta con citas, métricas, integridad del modelo relacional).
- Pruebas de la API: 26 casos de permisos por rol, validación de parámetros y
  restauración de versiones, todos correctos.
- Medición de la memoria (sección 4).

## 10. Limitaciones conocidas

- **Sin OCR:** los PDF escaneados o las diapositivas que son solo imagen no
  aportan texto (un documento real tenía alrededor del 50 % de páginas así).
- **Corpus de demostración:** un reglamento sintético corto y una presentación real de la UTPL. Falta el corpus oficial completo.
- Alucinación residual en preguntas **cercanas** al dominio que pasan el umbral
  pero cuya respuesta exacta no está en los documentos.
- El troceo es por número de caracteres, no por estructura (secciones o artículos).
- SQLite admite un solo escritor a la vez: suficiente para el piloto, no para miles de usuarios simultáneos.
- La evaluación por palabras clave de la medición de memoria es aproximada; falta RAGAS.
- La reescritura añade una llamada al modelo por turno (+1 s y +33 % de tokens).
- Cuota gratuita de Groq: 200.000 tokens al día (unas 80 preguntas con la memoria nueva).

## 11. Pendiente

1. OE4: evaluación con RAGAS (fidelidad, relevancia, precisión del contexto) y piloto con estudiantes y encuesta SUS.
2. Cargar el corpus oficial.
3. Mejorar el documento escrito del TIC: tiempo verbal uniforme, introducción y síntesis por capítulo, capítulos conectados.

## 12. Preguntas para el revisor

1. ¿La memoria con resumen y reescritura justifica su costo (+33 % tokens, +1 s)
   frente a la concatenación, viendo la medición? ¿Convendría reescribir solo
   cuando la regla detecta un seguimiento, para ahorrar llamadas? (Contra: la
   regla es justamente lo que falla con las referencias lejanas.)
2. Con un tope de 200.000 tokens al día en el plan gratuito, ¿qué recomendarías
   para un piloto: otro proveedor, un modelo más pequeño solo para reescribir, o caché?
3. ¿Es correcta la decisión de no tener "notas importantes" persistentes por el riesgo de propagar errores?
4. ¿El umbral fijo de distancia (0.65) es razonable, o convendría un re-ranker o un umbral relativo?
5. ¿El modelo de datos está bien normalizado para el alcance? ¿Sobra o falta algo?
6. ¿El esquema de permisos por rol tiene huecos?
7. ¿Qué métricas de RAGAS y qué tamaño de conjunto de preguntas serían defendibles para un TIC?
8. Con un corpus pequeño, ¿convendría trocear por estructura (artículos o secciones) en vez de por caracteres?
