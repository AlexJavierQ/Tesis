# Diseño de la arquitectura

## Vista de contenedores (nivel C4-2)

```mermaid
flowchart LR
    subgraph Cliente["Cliente (navegador)"]
        S[Streamlit]
        R[React SPA]
        W[Widget en portal]
    end

    subgraph Servidor["Servidor (Python)"]
        A[API REST - FastAPI]
        N[Núcleo RAG]
    end

    subgraph Datos["Almacenes"]
        Ch[(ChromaDB<br/>vectores)]
        U[(SQLite<br/>usuarios)]
        M[(SQLite<br/>métricas)]
        F[/PDF en disco/]
    end

    LLM[[Groq · gpt-oss-20b]]

    S -->|import directo| N
    R -->|HTTP JSON| A
    W -->|HTTP JSON| A
    A --> N
    N --> Ch
    N --> LLM
    N --> M
    A --> U
    N --> F
```

**Puntos clave:**
- Streamlit es la única interfaz que llama al núcleo directamente. Las
  otras dos pasan por la API REST. Esto se hizo así porque Streamlit
  vive en el mismo proceso Python, mientras React y el widget son
  clientes remotos.
- El núcleo NO conoce las interfaces. Se puede sumar una cuarta
  (Telegram bot, app móvil...) sin tocar `nucleo/`.

---

## Vista de componentes del núcleo (nivel C4-3)

```mermaid
flowchart TD
    RAG[rag.py<br/>orquestador]
    CFG[config.py]
    ING[ingest.py]
    LLM[llm.py]
    VS[vectorstore.py]
    EMB[embeddings.py]
    PDF[pdfreader.py]
    MET[metricas.py]
    AUT[auth.py]

    RAG --> VS
    RAG --> LLM
    ING --> PDF
    ING --> VS
    VS --> EMB
    LLM -.->|lee GROQ_API_KEY| CFG

    style RAG fill:#4d80e6,color:#fff
    style AUT fill:#e0b968,color:#000
```

Cada archivo es un **adaptador** de una herramienta concreta. Cambiar
la herramienta = reescribir el archivo, sin tocar el resto.

Ejemplos:
- Sustituir ChromaDB por Qdrant → reescribir `vectorstore.py`.
- Sustituir Groq por OpenAI → reescribir `llm.py`.
- Sustituir MiniLM por multilingual-e5 → una línea en `embeddings.py`.

---

## Flujo de una consulta

```mermaid
sequenceDiagram
    autonumber
    actor U as Estudiante
    participant F as Frontend
    participant A as API
    participant R as rag.py
    participant V as vectorstore
    participant L as LLM (Groq)

    U->>F: "¿cuántas horas necesito?"
    F->>A: POST /preguntar
    A->>R: responder(pregunta, carrera, curso)
    R->>V: buscar(pregunta, k=8, filtro)
    V-->>R: 8 fragmentos + distancias

    alt distancia_min > 0.65
        R-->>A: ABSTENCION (sin llamar al LLM)
    else hay fragmentos cercanos
        R->>L: prompt con contexto
        L-->>R: respuesta redactada
        R->>R: si LLM dijo "no tengo" → ABSTENCION
    end

    R-->>A: {respuesta, citas, con_respaldo}
    A->>A: metricas.registrar()
    A-->>F: JSON
    F-->>U: muestra respuesta + citas clicables
```

---

## Flujo de la ingesta

```mermaid
sequenceDiagram
    autonumber
    actor C as Coordinación
    participant F as Frontend
    participant A as API
    participant I as ingest.py
    participant P as pdfreader
    participant V as vectorstore

    C->>F: sube un PDF
    F->>A: POST /documentos
    A->>A: verifica rol (docente/coordinación)
    A->>A: guarda PDF en datos/docs/...
    A->>I: indexar_pdf(path, scope)
    I->>P: paginas_texto(path)
    P-->>I: lista de textos (uno por página)

    loop cada página
        I->>I: trocear(texto) → fragmentos de 500 chars con solape 80
    end

    I->>V: agregar(textos, metadatos, ids)
    V->>V: calcula embeddings (MiniLM)
    V->>V: guarda vectores + metadatos
    I-->>A: nº fragmentos indexados
    A-->>F: {ok: true, fragmentos: N}
```

---

## Flujo de autenticación

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as Frontend
    participant A as API
    participant Au as auth.py
    participant DB as usuarios.db

    Note over U,DB: LOGIN
    U->>F: (usuario, password)
    F->>A: POST /login {usuario, password}
    A->>Au: login(usuario, password)
    Au->>DB: SELECT password FROM usuarios WHERE usuario=?
    DB-->>Au: hash guardado
    Au->>Au: PBKDF2(password) == hash ?
    alt credenciales OK
        Au->>DB: INSERT sesiones (token, usuario, ahora)
        Au-->>A: token
        A-->>F: {token, usuario}
        F->>F: localStorage.setItem("token", ...)
    else credenciales inválidas
        Au-->>A: None
        A-->>F: 401
    end

    Note over U,DB: PETICIÓN PROTEGIDA
    F->>A: GET /documentos<br/>Authorization: Bearer <token>
    A->>Au: usuario_de(token)
    Au->>DB: JOIN sesiones/usuarios WHERE token=?
    DB-->>Au: {usuario, rol, carrera} o None
    Au-->>A: usuario
    A->>A: valida rol si aplica
    A-->>F: documentos
```

---

## Requisitos no funcionales (cómo los cumplimos)

| Requisito | Cómo se cumple | Dónde se ve |
|---|---|---|
| RNF1 · Precisión con respaldo documental | Umbral 0.65 + prompt restrictivo + cita literal | `rag.py:responder` |
| RNF2 · Trazabilidad | Cada respuesta incluye archivo + página exacta | `rag.py:citas`, visor PDF |
| RNF3 · Latencia < 8 s | Recuperación ~17 ms + LLM ~1 s = ~1 s típico | Medido en `evaluacion/evaluacion.py` |
| RNF4 · Privacidad | Métricas sin identificador de usuario | `metricas.py` |
| RNF5 · Extensibilidad | Adaptadores aislados | núcleo modular |
| RNF6 · Autenticación por rol | Login con hash + tokens + `_exigir` por endpoint | `auth.py`, `api.py` |

---

## Decisiones que conviene defender explícitamente

1. **Orquestación propia (sin LangChain).** El flujo cabe en 100 líneas
   y mantenerlo explícito nos permite intercambiar componentes.
2. **Groq como proveedor LLM por defecto.** Cuota gratuita generosa,
   sin tarjeta. Modelo actual: `openai/gpt-oss-20b`.
3. **Chunk = 500 caracteres con solape 80.** Medido en 3 tamaños
   (300/500/800). 500 fue el óptimo (ver `RESULTADOS_PRUEBAS.md`).
4. **PBKDF2-HMAC-SHA256 con 200.000 iteraciones para passwords.**
   Estándar NIST, sin dependencias externas (viene con Python).
5. **Token opaco en tabla en vez de JWT.** Más simple, revocación
   instantánea, no requiere clave de firma.
6. **Tres frontends, un solo backend.** Demuestra que la arquitectura
   está bien desacoplada.
