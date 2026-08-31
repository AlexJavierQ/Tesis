# Guía de aprendizaje del código

Documento para estudiar el sistema archivo por archivo antes de la defensa.
Léelo en el orden en que aparece: cada sección explica el rol del archivo,
las líneas clave y "qué diría yo si me preguntan por esto".

---

## Idea de fondo (30 segundos)

El sistema es un chatbot que responde preguntas sobre el reglamento del
Prácticum. La diferencia con ChatGPT es que **solo puede responder con lo
que dicen los documentos oficiales de la UTPL**. Si el reglamento no lo
dice, se abstiene y te deriva a coordinación.

Esa técnica se llama **RAG** (Retrieval Augmented Generation):

1. **Retrieval** — buscar los fragmentos de reglamento más parecidos a la
   pregunta.
2. **Augmented** — meter esos fragmentos como contexto en el prompt.
3. **Generation** — el LLM redacta la respuesta usando SOLO ese contexto.

Analogía útil en la defensa: *"Es un examen a libro abierto. El modelo
no estudió los reglamentos: cuando le preguntan, los busca y responde
con lo que encuentra."*

---

## Mapa de archivos

```
mvp_practicum/
├── nucleo/              ← el motor (Python puro)
│   ├── config.py        Carga las API keys
│   ├── pdfreader.py     Lee PDFs
│   ├── embeddings.py    Convierte texto en vectores
│   ├── vectorstore.py   Base vectorial (ChromaDB)
│   ├── llm.py           Llama al modelo de lenguaje (Groq)
│   ├── ingest.py        Prepara los documentos e indexa
│   ├── rag.py           ORQUESTADOR: la lógica de "responder"
│   ├── auth.py          Login (usuarios y sesiones)
│   └── metricas.py      Registra consultas anónimas
├── interfaces/          ← las 3 interfaces
│   ├── api.py           API REST (FastAPI)
│   ├── streamlit/       Interfaz Streamlit (Python)
│   ├── react/           Interfaz React (Vite)
│   └── widget/          Widget embebible (JS puro)
└── datos/               ← datos locales (no versionados)
    ├── docs/            corpus PDF
    ├── chroma_db/       índice vectorial
    ├── consultas.db     métricas
    └── usuarios.db      login
```

---

## nucleo/config.py (28 líneas)

**Qué hace:** carga la API key de Groq desde `.streamlit/secrets.toml`
o desde variables de entorno.

**Líneas clave:**
- `SECRETS = os.path.join(...)` — dónde vive el archivo con las claves.
- `os.environ.setdefault(...)` — solo escribe si NO existe ya en el entorno
  (así el servidor de producción puede inyectar la key sin editar archivos).
- `hay_key()` — devuelve `True` si hay clave configurada, `False` si no
  (en ese caso el sistema funciona en "modo degradado": muestra los
  fragmentos del reglamento crudos, sin que el LLM los redacte).

**Pregunta esperada:** *"¿Por qué la key no está en el código?"*
Respuesta: por seguridad (nunca se sube al repo) y para desacoplar
configuración de código.

---

## nucleo/pdfreader.py (23 líneas)

**Qué hace:** extrae texto de PDFs y los rasteriza en imagen para el visor.

**Líneas clave:**
- `paginas_texto(path)` — devuelve una lista con el texto de cada página.
- `render_png(path, pagina)` — convierte una página en imagen PNG (para
  mostrarla en el visor de citas del frontend).

**Herramienta:** PyMuPDF (importada como `fitz`). Se eligió porque es
**2.3 veces más rápida que pypdf** extrayendo el mismo texto (ver
`RESULTADOS_PRUEBAS.md`).

---

## nucleo/embeddings.py (25 líneas)

**Qué hace:** convierte texto en un vector de números.

**Concepto clave — embedding:** un vector de 384 números que representa
el **significado** del texto. Textos con significado parecido → vectores
cercanos en el espacio. Así el sistema "entiende" que
*"cuántas horas necesito"* y *"total de horas del prácticum"* son la
misma pregunta, aunque las palabras sean distintas.

**Modelo:** `paraphrase-multilingual-MiniLM-L12-v2`.
Multilingüe (español), ligero, rápido.

**Pregunta esperada:** *"¿Por qué multilingüe si es solo español?"*
Respuesta: porque los reglamentos mezclan español académico con
tecnicismos, y este modelo maneja bien esa mezcla. Además, si mañana
llegan documentos en inglés, no hay que cambiar nada.

---

## nucleo/vectorstore.py (60 líneas)

**Qué hace:** guarda los fragmentos con sus vectores y sabe buscar por
similitud.

**Herramienta:** **ChromaDB**. Se eligió porque:
- Guarda los METADATOS junto a cada vector (necesario para citar la fuente).
- Corre en local, sin costo, sin servidor.
- Usa métrica coseno para la similitud (`hnsw:space: cosine`).

**Función clave — `buscar(pregunta, k, filtro)`:**
1. Convierte la pregunta en vector.
2. Devuelve los `k` fragmentos con vector más cercano.
3. El `filtro` permite acotar por `scope` (por ejemplo, solo reglamentos
   de la carrera "computacion").

**Devuelve:** lista de `{texto, meta, distancia}`. La `distancia` es un
número entre 0 (idéntico) y 2 (opuesto). Cuanto menor, más parecido.

---

## nucleo/llm.py (43 líneas)

**Qué hace:** habla con el modelo de lenguaje (Groq, gpt-oss-20b de OpenAI).

**Por qué Groq:** cuota gratuita generosa, sin tarjeta, buena calidad
para tareas RAG. El modelo `openai/gpt-oss-20b` reemplaza a Llama 3.1
que Groq deprecó en 2026. Ver `ALTERNATIVAS_LLM.md`.

**Función `generar(prompt)`:** un POST HTTP a la API de Groq con el
prompt. Devuelve el texto o `None` si falla.

**Detalle importante:** `try/except` que devuelve `None` en cualquier
error. **Nunca lanza**. Eso permite el modo degradado: si el LLM cae,
el sistema sigue mostrando los fragmentos crudos.

**Temperatura = 0.2:** baja para que el modelo se pegue al contexto y
no invente. 0 sería determinista pero menos natural; 0.7-1.0 sería
creativo pero peligroso.

---

## nucleo/ingest.py (85 líneas)

**Qué hace:** prepara los documentos. Solo se corre cuando llega un PDF
nuevo o cuando se reindexa todo.

**Flujo (función `indexar_pdf`):**
1. Lee el PDF página por página con `pdfreader.paginas_texto`.
2. Cada página se pasa por `trocear(texto)`, que la parte en fragmentos
   de ~500 caracteres con 80 de solape.
3. Cada fragmento se guarda en ChromaDB con sus metadatos: archivo,
   página, ámbito (`scope`) y ruta.

**Por qué chunk de 500:** medido en `pruebas_herramientas.py`:
- 300 caracteres → 83% precisión (muy chico, fragmenta demasiado).
- **500 → 100% precisión.** ← el óptimo.
- 800 → 67% (muy grande, mezcla temas).

**Por qué solape de 80:** si una frase importante cae justo en el
borde de un trozo, el solape asegura que aparezca ENTERA en el trozo
vecino.

---

## nucleo/rag.py (110 líneas) — el más importante

**Qué hace:** orquesta todo el flujo de responder. Es el archivo que
más te van a preguntar.

**Constantes clave (líneas 14-17):**
- `TOP_K = 8` — recuperar 8 fragmentos por consulta. Salió de un barrido:
  con 5 el recall es 84%; con 8 sube a 93%; a partir de 12 no mejora y
  ocupa más contexto.
- `UMBRAL = 0.65` — si el mejor fragmento está a más de 0.65 de distancia,
  se abstiene sin llamar al LLM. Es la **capa anti-alucinación principal**.
- `MAX_CITAS = 3` — máximo 3 fuentes distintas mostradas al usuario.

**Función principal — `responder(pregunta, carrera, curso)`:**

```
1. scopes = ambitos donde puede buscar (global + curso si aplica)
2. hits = vectorstore.buscar(pregunta, k=8, filtro=scopes)
3. Si no hay hits           -> "aún no hay documentos"
4. Si distancia_min > 0.65  -> ABSTENCION (capa anti-alucinación)
5. Preparar citas (máx 3 fuentes distintas)
6. Construir prompt con contexto -> llm.generar()
7. Si LLM falló             -> mostrar fragmentos crudos
8. Si LLM dijo "no tengo"   -> ABSTENCION sin citas
9. Devolver respuesta + citas + con_respaldo
```

**El prompt (función `_prompt`):**
```
Eres el asistente de Practicum de la UTPL. Responde SOLO usando el
contexto que sigue. Si el dato exacto no está en el contexto, contesta
EXACTAMENTE esto y nada más: {ABSTENCION}
...
Contexto: [fragmentos]
Pregunta: [pregunta]
```

Tres instrucciones clave: (1) solo con el contexto, (2) frase exacta de
abstención (la usamos luego para detectar que se abstuvo), (3) formato de
respuesta con cita al final.

**Ámbitos (scopes):**
- `"computacion|global"` — reglamentos generales de Computación.
- `"computacion|curso:algoritmos"` — documentos del curso Algoritmos.

Así un documento subido a un curso NO se filtra al chat general.

---

## nucleo/auth.py (100 líneas)

**Qué hace:** sistema de login. Tres roles: `estudiante`, `docente`,
`coordinacion`.

**Tablas SQLite:**
- `usuarios(usuario, password, rol, carrera)` — la password guardada NO
  es la real, es un hash.
- `sesiones(token, usuario, creado_en)` — cuando alguien hace login, se
  crea un token opaco de 32 bytes y se guarda aquí.

**Hasheo (`_hashear`):** usa **PBKDF2-HMAC-SHA256 con sal aleatoria y
200.000 iteraciones**. Es un estándar recomendado por NIST. La sal es
distinta por usuario, así que dos usuarios con la misma contraseña
tienen hashes distintos (esto frena ataques de tabla arcoíris).

**Función `login(usuario, password)`:**
1. Busca al usuario en la tabla.
2. Verifica el hash con `_verificar`.
3. Genera un token con `secrets.token_urlsafe(32)`.
4. Guarda `(token, usuario, fecha)` en `sesiones`.
5. Devuelve el token.

**Función `usuario_de(token)`:** dado un token, devuelve el `{usuario,
rol, carrera}` o `None` si el token no existe.

**Seed automático:** la primera vez que se importa el módulo, si la
tabla está vacía, crea 3 usuarios demo:
- `estudiante` / `demo2026`
- `docente`    / `demo2026`
- `coord`      / `demo2026`

**Pregunta esperada:** *"¿Por qué no JWT?"*
Respuesta: JWT es overkill para un sistema con un solo backend. El token opaco en tabla es más
simple, permite revocar sesiones al instante (basta borrar la fila) y
no necesita firma criptográfica. Para producción sí se cambiaría.

---

## nucleo/metricas.py (65 líneas)

**Qué hace:** registro anónimo de consultas para saber qué se pregunta más.

**Tabla SQLite:**
`consultas(ts, pregunta, respondida, ambito)`

**Privacidad:** NO se guarda quién preguntó. Solo el texto de la pregunta,
la fecha, si tuvo respaldo y el ámbito. Coordinación ve totales, no
usuarios individuales.

**`resumen(filas)`:** cuenta totales, agrupa preguntas por texto exacto
(las 8 más frecuentes) y lista las preguntas sin respaldo (pistas de
qué documentos faltan).

---

## interfaces/api.py (180 líneas)

**Qué hace:** API REST con FastAPI. Todas las interfaces la consumen.

**Endpoints públicos (sin login):**
- `GET /salud` — estado del servicio.
- `GET /carreras`, `/carreras/{c}/cursos` — estructura.
- `POST /login` — devuelve token.
- `POST /preguntar` — chat (público para que el widget funcione).

**Endpoints protegidos (con `Authorization: Bearer <token>`):**
- `GET /me` — quién soy.
- `POST /logout`.
- `GET /documentos`, `GET /documentos/pagina`, `GET /documentos/info`
  — cualquier sesión.
- `POST /documentos`, `DELETE /documentos` — solo docente/coordinación.
- `GET /metricas` — solo coordinación.

**Seguridad implementada:**

1. **Autorización por rol.** La función `_exigir(auth, *roles)` valida
   token Y opcionalmente el rol. Si algo falla, lanza 401 o 403.

2. **Anti path-traversal (`_resolver_ruta`).** Cuando el cliente pide
   `/documentos/pagina?ref=xxx`, se comprueba con `os.path.commonpath`
   que la ruta resuelta caiga DENTRO de `datos/docs/`. Sin esto, un
   `?ref=../../../etc/passwd` serviría cualquier archivo del disco.

3. **CORS restrictivo.** Solo acepta orígenes declarados en la variable
   `CORS_ORIGINS`. Por defecto: `localhost:5173` (React) y `:5500` (widget).

---

## interfaces/streamlit/streamlit_app.py (155 líneas)

Interfaz "todo en Python". Un solo archivo, sin frontend aparte.

**Flujo:**
1. Si no hay token en `session_state`, muestra `pantalla_login()` y
   detiene el script con `st.stop()`.
2. Con sesión: lee `rol` del usuario y arma la barra lateral con las
   opciones según el rol.
3. Cada sección (`seccion_chat`, `seccion_mis_cursos`,
   `seccion_documentos`, `seccion_metricas`) es una función independiente.

**Nota:** la Streamlit llama al núcleo (`rag.responder`) DIRECTAMENTE,
no pasa por la API. Es la interfaz más simple pero también la menos
"pura" desde el punto de vista arquitectónico.

---

## interfaces/react/ (7 archivos, ~350 líneas totales)

Interfaz web moderna con React + Vite.

**Archivos:**
- `main.jsx` — punto de entrada estándar de React.
- `App.jsx` — decide qué mostrar: `Login` si no hay sesión, `Chat` o
  `Admin` si hay.
- `api.js` — cliente HTTP. Todas las llamadas pasan por aquí. Guarda
  el token en `localStorage` para que sobreviva al F5.
- `componentes/Login.jsx` — formulario de login.
- `componentes/Chat.jsx` — chat del estudiante.
- `componentes/Admin.jsx` — gestión de documentos (docente/coordinación)
  y métricas (solo coordinación).
- `estilos.css` — un solo archivo con todos los estilos.

**Patrón clave:** el estado del usuario vive en `App.jsx`. Cuando
`Login` autentica bien, llama `onOk(usuario)` que sube el estado al
padre.

---

## interfaces/widget/asistente-widget.js (165 líneas)

Chat flotante embebible en cualquier portal web.

**Decisión clave — Shadow DOM:**
El widget se inyecta en portales que tienen SU propio CSS (posiblemente
hostil). El `attachShadow({mode: "open"})` crea una frontera de estilos:
- Hacia dentro: el CSS del portal no alcanza el widget.
- Hacia fuera: los estilos del widget no rompen el portal.

**Sin login:** el widget habla con `/preguntar`, que es público.
Perfecto para que el estudiante consulte sin registrarse.

**Integración:** una sola línea en el portal:
```html
<script src="asistente-widget.js"
        data-api="https://api.utpl.edu.ec"
        data-carrera="computacion"></script>
```

**Seguridad — `textContent` en lugar de `innerHTML`:** el texto del
LLM y los nombres de archivo son datos externos. Insertarlos con
`innerHTML` sería una vía de inyección XSS. Con `textContent` el
navegador los trata como texto plano, no HTML.

---

## Cómo repasar en 2 días

**Sábado:**
- Leer `rag.py` línea por línea. Es el más importante y el que
  te van a preguntar. Entender los 6 pasos de `responder()`.
- Leer `ingest.py` y entender por qué chunk=500 y solape=80.
- Correr la app en local y hacer 5 preguntas dentro del corpus y 5
  fuera para ver el umbral de abstención en acción.

**Domingo:**
- Leer `api.py` y saber qué endpoint hace qué.
- Leer `auth.py` y saber explicar el hash con sal.
- Ensayar la demo: login como estudiante → pregunta → ver cita en el
  visor. Login como coordinación → subir un PDF → ver que aparece en
  las respuestas.

## Preguntas frecuentes del tribunal (anticípalas)

1. **"¿Por qué no usan LangChain?"**
   Porque el flujo cabe en 100 líneas y mantenerlo explícito nos
   permite cambiar cualquier herramienta (embeddings, LLM, base
   vectorial) tocando un solo archivo.

2. **"¿Cómo saben que no inventa?"**
   Tres capas: (1) umbral de similitud antes de llamar al LLM, (2)
   prompt que le prohíbe usar conocimiento propio, (3) toda respuesta
   viene con cita a la página exacta del PDF, verificable por el usuario.

3. **"¿Qué pasa si el LLM cae?"**
   Modo degradado: `llm.generar()` devuelve `None`, el orquestador
   detecta esto y muestra los fragmentos oficiales crudos con su fuente.
   El servicio nunca se cae.

4. **"¿Por qué SQLite y no PostgreSQL?"**
   Es un sistema piloto. SQLite basta para volúmenes de piloto (miles de consultas),
   no requiere servidor, corre en el mismo archivo. Para producción
   universitaria se migraría a Postgres.

5. **"¿Cómo escala?"**
   Los cuellos de botella son (1) la latencia del LLM (~1 s por
   consulta, mitigable con caché de preguntas frecuentes), y (2)
   ChromaDB en un solo proceso (para producción se movería a Qdrant
   o Weaviate, y la interfaz `vectorstore.py` se reimplementa sin
   tocar el resto).
