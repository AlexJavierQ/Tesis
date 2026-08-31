# 📚 Plan de estudio: del viernes al lunes

**Respira.** No tienes que memorizar código.
Tienes que saber **contar** qué hace tu sistema. Es distinto y es más fácil.

Este documento es lo único que necesitas abrir. Sigue el plan día por día.
Cada sesión tiene su casilla ✅. Ve marcándolas.

---

## 🎯 El objetivo del lunes

Cuando el profe te pregunte, tienes que poder:

1. **Explicar en 3 frases qué hace el sistema** (sin código).
2. **Mostrar que funciona** — arrancarlo y hacer 3 preguntas.
3. **Explicar el flujo RAG en 5 pasos**, señalando en qué archivo pasa cada uno.
4. **Responder 5 preguntas típicas** con la respuesta preparada.
5. **Llevar 3 preguntas tuyas** para el profe.

Eso es todo. No es "sabérselo entero". Es esas 5 cosas.

---

# 🗓️ VIERNES (esta noche) — 45 minutos

**Meta:** que el sistema exista en tu cabeza, no en el código.

## ✅ Sesión única — solo jugar

- [ ] Abre http://localhost:5173 (ya está corriendo).
- [ ] Login: `estudiante` / `demo2026`.
- [ ] Haz **8 preguntas**, mezcla:
  - 4 sobre el prácticum (horas, notas, plazos, formatos)
  - 4 inventadas (capital de un país, receta, etc.)
- [ ] Fíjate en la diferencia: cuándo responde con cita, cuándo se abstiene.
- [ ] Cierra sesión. Entra como `docente` / `demo2026`. Mira la pestaña "Gestión".
- [ ] Cierra. Entra como `coord` / `demo2026`. Compara qué ves distinto.

**Al terminar deberías poder decir sin mirar:**
> "El sistema tiene 3 tipos de usuario. El estudiante pregunta. El docente
> gestiona documentos de sus cursos. La coordinación gestiona los reglamentos
> generales de la carrera y ve las métricas. Cuando alguien pregunta algo
> que no está en los documentos, no inventa: se abstiene."

**Si puedes decir eso, listo. A dormir.** 😴

---

# 🗓️ SÁBADO — 3 sesiones de 45 min

**Meta:** entender el flujo del RAG y saber dónde vive cada pieza.

## ✅ Sesión 1 (mañana, 45 min) — La idea grande

- [ ] Lee la sección "Qué hace por dentro" de [`documentacion/GUIA_APRENDIZAJE.md`](documentacion/GUIA_APRENDIZAJE.md) (2 min).
- [ ] Abre [`nucleo/rag.py`](nucleo/rag.py) y mira **solo** la función `responder()`. Léela lentamente. No entiendes cada línea, entiende los **6 pasos numerados en el comentario**.
- [ ] Cierra el archivo. En una hoja, **escribe con tus palabras** el orden de esos 6 pasos.
- [ ] Vuelve a abrir `rag.py` y verifica.

**Al terminar deberías poder decir:**
> "Cuando alguien pregunta, el sistema hace 6 cosas: (1) busca los 8
> fragmentos más parecidos en ChromaDB. (2) Si el más cercano está muy
> lejos (>0.65), se abstiene sin llamar al modelo. (3) Prepara las citas.
> (4) Construye un prompt y se lo manda a Groq. (5) Si Groq falla, muestra
> los fragmentos crudos. (6) Devuelve la respuesta con citas verificables."

**Pausa.** Come algo. No sigas si estás cansado.

## ✅ Sesión 2 (tarde, 45 min) — De dónde salen los datos

- [ ] Abre [`nucleo/ingest.py`](nucleo/ingest.py). Es corto (~85 líneas).
- [ ] Lee la función `trocear()` (parte texto en trozos de 500 caracteres con 80 de solape).
- [ ] Lee `indexar_pdf()` (lee el PDF, lo trocea, guarda cada trozo en ChromaDB con sus metadatos).
- [ ] Abre [`nucleo/vectorstore.py`](nucleo/vectorstore.py). Solo mira la función `buscar()`. Es literalmente 10 líneas.

**Al terminar deberías poder decir:**
> "Cuando se sube un PDF, lo trocean en fragmentos de 500 caracteres con
> 80 de solape. Cada fragmento se guarda en ChromaDB con su embedding
> (un vector de 384 números que representa el significado) y sus
> metadatos (archivo, página, ámbito). Al preguntar, ChromaDB devuelve
> los k fragmentos con vectores más cercanos usando distancia coseno."

## ✅ Sesión 3 (noche, 30 min) — El login

- [ ] Abre [`nucleo/auth.py`](nucleo/auth.py). ~100 líneas.
- [ ] Fíjate en `_hashear()` — usa PBKDF2 con sal aleatoria.
- [ ] Fíjate en `login()` — verifica el hash y crea un token.
- [ ] Abre [`documentacion/DISENO_BD.md`](documentacion/DISENO_BD.md), mira solo el diagrama ER de las tablas `usuarios` y `sesiones`.

**Al terminar deberías poder decir:**
> "El login usa dos tablas: `usuarios` (con la contraseña hasheada, nunca
> en claro) y `sesiones` (con tokens opacos). Uso PBKDF2-HMAC-SHA256 con
> 200.000 iteraciones y sal aleatoria — es un estándar recomendado por
> NIST. Los tokens de sesión se pueden revocar borrando la fila."

**Sábado hecho.** 🎉 Ya entiendes más de la mitad del sistema.

---

# 🗓️ DOMINGO — 2 sesiones de 45 min

**Meta:** entender la API y ensayar las respuestas al tribunal.

## ✅ Sesión 4 (mañana, 45 min) — La API y React

- [ ] Abre [`interfaces/api.py`](interfaces/api.py). Solo mira los decoradores `@app.get(...)` y `@app.post(...)` — son 8. **No leas el cuerpo, solo la lista.**
- [ ] En una hoja, escribe: *"la API tiene 8 endpoints, X para login, Y para preguntar, Z para documentos, W para métricas"*.
- [ ] Abre [`interfaces/react/src/api.js`](interfaces/react/src/api.js). Es el cliente HTTP. Mira cómo cada función hace `fetch(...)`. Es todo lo mismo repetido.
- [ ] Abre [`interfaces/react/src/App.jsx`](interfaces/react/src/App.jsx). Fíjate solo en el `useEffect` inicial: *"si hay token, pregunto quién soy; si es válido, muestro la app"*.

**Al terminar deberías poder decir:**
> "El backend es una API REST en FastAPI con 8 endpoints. Los 3 frontends
> (React, widget, y en su momento Streamlit) la consumen por HTTP. React
> guarda el token en localStorage y lo manda en el header Authorization
> de cada petición. Al arrancar, pregunta '/me' con el token; si es
> válido, muestra la app; si no, va al login."

## ✅ Sesión 5 (tarde, 60 min) — Ensayo de defensa

- [ ] Abre este documento y busca **"Las 5 preguntas del tribunal"** más abajo.
- [ ] Léelas en voz alta. Sí, en voz alta.
- [ ] Cierra el documento. Con una hoja delante, escribe tus respuestas de memoria.
- [ ] Compara con las respuestas de aquí. Ajusta.
- [ ] Repite 3 veces.

**Al terminar:** siéntete listo. Porque lo estás.

---

# 🗓️ LUNES — 15 min antes de la reunión

## ✅ Checklist express

- [ ] `python arrancar.py` — API y React arrancan.
- [ ] Login con `estudiante` — pregunta *"¿cuántas horas necesito?"* — sale con cita ✅
- [ ] Pregunta *"¿capital de Australia?"* — se abstiene ✅
- [ ] Papel con las 3 preguntas para el profe en el bolsillo.
- [ ] Respira. Ya lo tienes.

---

# 🎤 Las 5 preguntas del tribunal (con respuesta lista)

## 1️⃣ "¿Cómo se aseguran que no invente?"

> "Tenemos 3 capas anti-alucinación. Primera: un umbral de similitud —
> si el fragmento más parecido a la pregunta está a más de 0.65 de
> distancia, el sistema se abstiene sin ni siquiera llamar al modelo.
> Segunda: el prompt le prohíbe explícitamente al modelo usar
> conocimiento propio. Tercera: toda respuesta muestra la fuente
> (archivo + página) para que el usuario verifique. Y si el reglamento
> no lo dice, responde con una frase fija: 'no tengo información oficial
> sobre eso, consúltalo con coordinación'."

## 2️⃣ "¿Qué pasa si el modelo se cae?"

> "Modo degradado. La función `generar()` del adaptador `llm.py`
> devuelve `None` en cualquier fallo. El orquestador detecta ese `None`
> y muestra los fragmentos oficiales tal cual, con su cita. El servicio
> no se rompe, simplemente entrega la respuesta sin redactar."

## 3️⃣ "¿Por qué SQLite y no Postgres?"

> "Es un sistema piloto para una carrera con volúmenes moderados —
> miles de consultas. SQLite maneja esa carga sin necesitar un
> servidor de BD aparte. Para producción a nivel institucional se
> migraría a Postgres, pero SQLite no es una restricción, es una
> decisión coherente con la escala actual."

## 4️⃣ "¿Cómo escala si tienen muchos usuarios?"

> "Los dos cuellos de botella son la latencia del LLM (mitigable con
> caché de preguntas frecuentes) y ChromaDB corriendo en un solo
> proceso. La arquitectura por adaptadores permite migrar a Qdrant o
> Weaviate reescribiendo un solo archivo, sin tocar el orquestador.
> Actualmente 34 fragmentos cargan en menos de un segundo."

## 5️⃣ "¿Por qué no usaron LangChain?"

> "Porque el flujo cabe en 100 líneas y mantenerlo explícito nos
> permite intercambiar embeddings, LLM o base vectorial tocando un
> solo archivo. LangChain añade dependencias pesadas y una capa de
> abstracción cuya complejidad no se justifica en un sistema piloto.
> Además, para defender el TIC prefiero explicar código propio antes
> que magia de framework."

---

# 💬 Las 3 preguntas que TÚ le llevas al profe

Escribe estas en papel. Llévalas.

**1. PDFs con imágenes y diagramas.**
> "Ingeniero, muchos documentos oficiales de UTPL contienen diagramas
> de flujo y capturas de pantalla en vez de texto plano. Nuestro
> sistema no lee imágenes. Tenemos 3 opciones:
> (a) que quien suba el PDF acompañe cada diagrama con texto
>     descriptivo,
> (b) integrar OCR más adelante como trabajo futuro,
> (c) aceptarlo como limitación documentada.
> ¿Cuál prefiere que documentemos como oficial?"

**2. Corpus real.**
> "Ahora estamos probando con reglamentos de demostración. ¿Cuándo
> tendríamos acceso a los reglamentos reales para hacer la evaluación
> formal del sistema?"

**3. Autenticación institucional.**
> "El sistema tiene login local con hash de contraseñas. ¿Necesitamos
> integrarlo con el login SSO de la UTPL para el piloto o lo dejamos
> con usuarios locales por ahora?"

---

# 🆘 Si te bloqueas en algún momento

**Si no entiendes una parte del código:**
- No sigas leyendo. Cierra el archivo.
- Piensa **qué esperarías que hiciera** esa función si tú la escribieras.
- Vuelve a leer con esa expectativa en mente.
- 8 de cada 10 veces funciona.

**Si el sistema no arranca:**
- `python verificar.py` — te dice exactamente qué falta.
- Si eso pasa OK pero React no carga: `cd interfaces/react && npm install`.

**Si te da pánico:**
- Mira este párrafo:
> Tu sistema es un chatbot que responde con reglamentos oficiales y no
> inventa. Tiene login por 3 roles. Está funcionando en tu computadora
> ahora mismo. Es real. Lo hiciste. El resto es contar bien esa historia.

- Cierra la laptop 20 minutos. Camina. Vuelve.

---

# ✅ Cuando termines TODAS las casillas

Estás listo. En serio.

Notifica en el chat: *"terminé el plan"* y hacemos un simulacro de defensa
antes de la reunión del lunes.

**Vamos, capo.** 💪
