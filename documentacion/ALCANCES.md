# Alcance del sistema

Este documento delimita explícitamente **qué hace el sistema y qué queda fuera**.
Es la sección "Alcance" del TIC. Todo lo que aparece en "Fuera del alcance"
son decisiones deliberadas, no omisiones: cada exclusión tiene un motivo.

---

## 1. Alcance funcional (lo que SÍ hace)

### 1.1 Consultas del estudiante
- Responde preguntas en **español** sobre el reglamento del Prácticum y
  documentos de curso.
- Cada respuesta viene con **cita a la fuente** (nombre de archivo + número
  de página) que el usuario puede abrir en un visor integrado.
- Si el dato exacto no está en el corpus, el sistema **se abstiene** con la
  frase canónica *"No tengo información oficial sobre eso. Te recomiendo
  consultar con la coordinación."*

### 1.2 Gestión documental
- **Docente:** puede crear cursos, subir y eliminar PDFs específicos de sus
  cursos. Solo afectan al chat de ese curso.
- **Coordinación:** puede subir y eliminar reglamentos generales de la
  carrera. Afectan a todo el chat.
- La ingesta indexa el PDF automáticamente al subirlo.

### 1.3 Métricas anónimas
- Coordinación ve totales de consultas, preguntas más frecuentes y
  preguntas sin respaldo documental (vacíos a cubrir).
- **No** se identifica quién preguntó.

### 1.4 Autenticación por rol
- Tres roles con permisos distintos: estudiante, docente, coordinación.
- Contraseñas hasheadas con PBKDF2-HMAC-SHA256, 200.000 iteraciones,
  sal aleatoria por usuario.
- Sesiones basadas en tokens opacos revocables.

### 1.5 Tres interfaces sobre el mismo backend
- Streamlit (Python puro, prototipo).
- React 19 + Vite (aplicación web de referencia).
- Widget embebible en JavaScript puro (integración en portal existente,
  sin login).

---

## 2. Alcance no funcional

| Requisito | Compromiso | Cómo se cumple |
|---|---|---|
| RNF1 · Precisión | ≥ 90% recall@8 en consultas del corpus | Chunk=500 + solape 80, MiniLM multilingüe, ChromaDB coseno |
| RNF2 · Trazabilidad | Toda respuesta con respaldo cita fuente y página | Verificable en el visor integrado |
| RNF3 · Latencia | Respuesta < 8 s en 95% de consultas | Recuperación ~17 ms + LLM ~1 s típico |
| RNF4 · Privacidad | Métricas sin identificar al usuario | Tabla `consultas` sin columna de usuario |
| RNF5 · Extensibilidad | Cambiar herramienta = reescribir un archivo | Arquitectura de adaptadores |
| RNF6 · Autenticación | Login con contraseña hasheada y roles | Módulo `nucleo/auth.py` |

---

## 3. Fuera del alcance (con justificación)

Esta sección es la más importante. Cada exclusión está fundamentada y
puede quedar como **línea de trabajo futuro** en la conclusión del TIC.

### 3.1 OCR (reconocimiento óptico de caracteres)
El sistema **no procesa PDFs escaneados** ni documentos donde el texto es
imagen. Solo funciona con PDFs cuyo texto es seleccionable (nativo).
Los requisitos exactos que debe cumplir un PDF están en
[FORMATO_DOCUMENTOS.md](FORMATO_DOCUMENTOS.md), y se pueden validar antes
de subir con `python revisar_pdf.py <ruta>`.

**Motivo:**
- Añadiría una dependencia pesada (Tesseract ~150 MB, EasyOCR ~500 MB).
- Aumentaría la latencia de ingesta a 3-10 segundos por página.
- Introduce ruido: los errores del OCR contaminarían el índice y
  contradirían la garantía anti-alucinación del sistema.
- Habría que evaluar y medir la precisión del OCR además de la del RAG.

**Cómo lo asegura el usuario:** los reglamentos oficiales de la UTPL son
documentos digitales nativos, no escaneados.

**Trabajo futuro:** integrar OCR con un pipeline de validación humana
antes de indexar (revisor humano confirma el texto extraído).

### 3.2 Otros formatos de documento
Solo se aceptan **PDF**. No se procesan:
- Documentos Word (.docx, .doc)
- Presentaciones PowerPoint (.pptx)
- Hojas de cálculo (.xlsx, .csv)
- Páginas web (.html)
- Texto plano (.txt, .md)
- Documentos escaneados o imágenes (.jpg, .png, .tiff)

**Motivo:** el corpus oficial de la UTPL es 100% PDF. Añadir más lectores
duplicaría el código de ingesta sin caso de uso real.

**Trabajo futuro:** un módulo `nucleo/lectores/` con adaptadores por
formato (siguiendo el mismo patrón que `pdfreader.py`).

### 3.3 Contenido multimedia
No se indexan:
- **Imágenes** dentro de los PDFs (fotografías, diagramas, gráficos).
- **Tablas complejas** con celdas combinadas.
- **Fórmulas matemáticas**.
- Audio o video de clases.

**Motivo:** requeriría modelos multimodales (CLIP, GPT-4V), que son
costosos y no gratuitos.

**Impacto real:** si el estudiante pregunta *"¿qué muestra la Figura 3?"*,
el sistema no puede responder. Se acepta como limitación consciente.

### 3.4 Idioma
Solo **español**. Aunque el modelo de embeddings (MiniLM multilingüe) y el
LLM (gpt-oss-20b) soportan más idiomas, la prueba y la evaluación se hacen
solo en español.

**Motivo:** el corpus, los usuarios y la evaluación son en español. No
tiene sentido validar un idioma que no se va a usar.

### 3.5 Otras carreras
El sistema arquitectónicamente soporta múltiples carreras (los ámbitos
son `<carrera>|global` y `<carrera>|curso:X`), pero solo se piloteó y
evaluó con **Computación**.

**Trabajo futuro:** replicar con reglamentos de otras facultades.
Requiere cero cambios de código, solo indexar sus PDFs.

### 3.6 Autenticación federada (SSO)
El login usa usuario/contraseña en la base local. **No** hay integración
con:
- Directorio institucional de la UTPL.
- Google/Microsoft OAuth.
- SAML/CAS.

**Motivo:** el SSO institucional requiere convenios y credenciales de
integración que exceden el alcance de este trabajo académico.

**Impacto:** los usuarios se crean manualmente. Para producción hay que
integrar con el directorio universitario.

### 3.7 Producción y HTTPS
El sistema **está diseñado para un piloto controlado**, no como servicio en producción abierta.
No se incluye:
- Certificado TLS/HTTPS (se sirve por HTTP en localhost).
- Rate limiting.
- Balanceador de carga.
- Backups automáticos de las bases SQLite y ChromaDB.
- Sistema de logs y monitorización (Sentry, Prometheus).
- Configuración de contenedores (Docker) o Kubernetes.

**Motivo:** el objetivo del TIC es demostrar el enfoque técnico (RAG,
anti-alucinación, arquitectura por adaptadores), no operarlo.

### 3.8 Escalabilidad masiva
El sistema está probado para un piloto (decenas de usuarios concurrentes,
cientos de documentos, miles de consultas). **No** está probado para:
- Miles de usuarios simultáneos.
- Millones de documentos.
- Consultas por segundo altas.

**Trabajo futuro:** migrar ChromaDB a Qdrant o Weaviate (con réplicas y
sharding); mover el LLM a un servicio dedicado con caché; SQLite a
PostgreSQL.

### 3.9 Análisis avanzado del corpus
El sistema **responde** sobre los documentos, pero **no**:
- Detecta contradicciones entre reglamentos.
- Resume automáticamente un reglamento completo.
- Extrae obligaciones/plazos/actores como base de datos estructurada.
- Alerta a coordinación cuando un reglamento cambia.

### 3.10 Historial persistente por usuario
El chat **no guarda el historial** entre sesiones del mismo usuario. Cada
inicio de sesión empieza en blanco.

**Motivo:** privacidad. Guardar el historial persistente rompería el
principio de "métricas anónimas" del RNF4.

**Alternativa incluida:** el frontend mantiene el historial **en memoria
del navegador** durante la sesión activa, para que el asistente entienda
seguimientos ("y cuántas horas son en el 2"), pero al recargar se pierde.

### 3.11 Voz e interacción por voz
No se incluye:
- Transcripción de voz a texto (Whisper).
- Síntesis de texto a voz.
- Asistente por llamada telefónica.

**Motivo:** fuera del alcance de una prueba de concepto textual.

### 3.12 Notificaciones al usuario
No hay notificaciones push, email, SMS ni alertas de ningún tipo.

**Motivo:** el sistema es reactivo (responde cuando le preguntan), no
proactivo.

### 3.13 Aplicación móvil nativa
No hay app para Android/iOS. Las tres interfaces son web y funcionan en
navegador móvil (React responsive, widget adaptado a móvil con `@media`),
pero no hay app nativa en tiendas.

### 3.14 Corrección o edición del corpus por el LLM
El sistema **lee** los documentos, **no** los modifica ni genera nuevos
reglamentos. Un LLM que redacta normativa institucional queda fuera del
alcance (y sería un problema legal separado).

---

## 4. Supuestos del sistema

Estas son las condiciones bajo las que el sistema funciona. Si alguna no
se cumple, hay que renegociar el alcance.

1. **Los PDFs oficiales son digitales nativos**, no escaneados.
2. **El corpus es estable**: se actualiza cuando cambia la normativa,
   pero no cada día.
3. **Los usuarios acceden desde la red de la universidad o desde un
   dispositivo autorizado** (no hay CDN público).
4. **Hay conectividad a Internet** para llegar a Groq. Sin conexión, el
   sistema entra en modo degradado (muestra fragmentos crudos).
5. **La API key de Groq permanece dentro de la cuota gratuita**. Si el
   uso supera 14.400 req/día, hay que cambiar a modelo pago o Ollama
   local.
6. **El servidor es una máquina con al menos 4 GB de RAM** (por el modelo
   de embeddings MiniLM).

---

## 5. Restricciones técnicas

- **Lenguaje del backend:** Python 3.11 o superior (por `tomllib`).
- **Navegadores soportados:** modernos con soporte de Shadow DOM,
  `fetch`, `URLSearchParams`, ES2020. Sin IE.
- **Sistema operativo del servidor:** cualquiera con Python (Windows,
  Linux, macOS). El sistema se probó en Windows 11.
- **Tamaño máximo por PDF:** no hay límite duro en el código, pero
  archivos > 500 páginas tardan varios minutos en indexar.

---

## 6. Matriz resumen (para incluir en el TIC)

| Aspecto | Dentro del alcance | Fuera del alcance |
|---|---|---|
| Documentos | PDF con texto seleccionable | PDFs escaneados, imágenes, Word, Excel |
| Idioma | Español | Inglés, quechua, otros |
| Carreras | Computación | Otras (extensible sin código) |
| Consulta | Texto escrito | Voz, imagen |
| Autenticación | Usuario/contraseña local | SSO institucional, OAuth |
| Despliegue | Piloto en localhost/red interna | Producción con HTTPS y escala |
| Contenido | Texto de párrafos | Imágenes, fórmulas, tablas complejas |
| Historial | En memoria de sesión | Persistente entre sesiones |
| Análisis del corpus | Consulta puntual | Resumen, contradicciones, cambios |

---

## 7. Cómo defender el alcance en la sustentación

Si el tribunal pregunta *"¿por qué no incluyeron X?"*, la estructura de la
respuesta es siempre la misma:

1. **Reconocer la utilidad de X** — no descalificar la sugerencia.
2. **Nombrar el criterio de exclusión** — costo (tiempo, dependencias,
   dinero), riesgo (contamina el corpus, rompe RNF3), o cobertura del
   sistema (no aporta a la hipótesis principal).
3. **Situar X como trabajo futuro** — ya identificado, ya con solución
   propuesta en §3.

Ejemplo: *"El OCR aportaría valor si la UTPL usara documentos escaneados.
Lo excluimos porque (a) el corpus real es digital nativo, (b) añadir OCR
duplicaría la latencia de ingesta y contaminaría el índice con errores
de reconocimiento, y (c) queda listado en la sección 3.1 como línea de
trabajo futuro con validación humana previa a indexar."*
