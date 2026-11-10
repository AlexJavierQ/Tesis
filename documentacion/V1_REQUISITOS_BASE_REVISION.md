# Línea base técnica de requisitos V1 — Asistente de Prácticum UTPL

**Corte:** 10/11/2026. **Estado:** especificación candidata congelada para revisión del 11/11/2026; **no validada ni aprobada institucionalmente**. Origen: propuesta de TT, matriz de Google Sheets v0.7 y diagnóstico del prototipo. No se inventan entrevistas, actas ni métricas.

> **Estado de implementación al 10/11/2026:** qué requisitos están implementados, parciales o pendientes, con su evidencia, está en [V1_ENTREGA_REVISION.md](V1_ENTREGA_REVISION.md) (sección 3). De las decisiones P0 listadas al final de este documento, dos ya tienen respuesta técnica en la rama: `/preguntar` exige sesión de estudiante y la analítica dejó de guardar la pregunta literal y el usuario (esquema v6). Siguen pendientes de decisión institucional.

**Objetivo general literal (propuesta):** Desarrollar una plataforma web basada en Retrieval-Augmented Generation (RAG) que asista las consultas de los estudiantes de Prácticum sobre prácticas preprofesionales.

**E2 literal:** Desarrollar el pipeline documental y el motor del agente con validación anti-alucinación.

**E3 literal:** Implementar las interfaces web del sistema: chat estudiantil con citación de fuentes y panel analítico del coordinador.

**E4 literal:** Evaluar el desempeño del agente y la usabilidad del prototipo con estudiantes de Prácticum.

## Reglas de interpretación

- Cada RF de la tabla es una **capacidad propuesta para V1**, con criterio verificable. «Propuesto» no significa aceptado por docentes/coordinación.
- La plataforma se plantea para un **piloto controlado**, no para operación universitaria pública.
- RF-21 (panel coordinador) se desprende expresamente de E3; RF-17 (analítica docente) es **extensión adicional por confirmar**.
- RF-28 (orientación a soporte humano) se deriva de la descripción C y la metodología E de la propuesta; no presupone automatizar tickets o inventar contactos.
- Los casos de prueba son un plan, no ejecuciones. Los umbrales de calidad se definen **antes** del piloto.

## Requisitos funcionales — alcance V1 propuesto (18)

| ID | Actor | Capacidad esperada | Criterio de aceptación observable | Objetivo | Prueba | Trazabilidad |
|---|---|---|---|---|---|---|
| **RF-01** | Estudiante | El estudiante inicia sesión con credenciales autorizadas para usar el chat con historial. | Con credenciales válidas accede; con inválidas no. Ningún usuario puede leer historial ajeno. | E3 · soporte a chat | U-01, A-01 | EP-02 · HU-05 / CU-01 |
| **RF-02** | Estudiante | El estudiante selecciona una carrera asignada; servidor comprueba permisos antes de recuperar material restringido. | Una carrera propia permite consulta; una ajena devuelve acceso denegado si la política la restringe. | E3 · ámbitos de consulta | U-01, S-01 | EP-02 · HU-06 / CU-02 |
| **RF-03** | Estudiante | El estudiante formula preguntas en lenguaje natural sobre documentos generales autorizados. | Caso con evidencia: respuesta fundamentada; caso sin evidencia: deriva a RF-07. | E2 + E3 · motor y chat | U-02, PR-E-01 | EP-01 · HU-01 / CU-03 |
| **RF-04** | Estudiante | El estudiante selecciona un curso disponible y consulta sus documentos. | Los resultados pertenecen al curso permitido; sin curso válido no se consulta ese ámbito. | E2 + E3 · búsqueda por curso | U-03, S-01 | EP-01 · HU-02 / CU-02, CU-04 |
| **RF-06** | Estudiante | El sistema presenta referencias verificables al documento y su ubicación. | Cada respuesta respaldada contiene referencia correcta; prueba coteja documento/página/versión con archivo real. | E2 + E3 · fuentes y citas | U-02, U-08, PR-E-01 | EP-01 · HU-03 / CU-03, CU-06 |
| **RF-07** | Estudiante | El asistente reconoce ausencia o insuficiencia de evidencia y no inventa respuestas. | Preguntas sin evidencia en banco de pruebas generan abstención; las de evidencia real tienen respaldo. | E2 · validación anti-alucinación | U-06, PR-E-01 | EP-01 · HU-01/HU-04 / CU-03, CU-18 |
| **RF-12** | Estudiante | Cada cita permite abrir directamente el documento o la página autorizada que respalda la respuesta, respetando permisos y versión documental. | Al pulsar una cita se muestra la página correcta con acceso y versión adecuados. | E3 · citación de fuentes | U-08 | EP-01 · HU-03 / CU-06 |
| **RF-13** | Docente | El docente visualiza sus cursos asignados y accede a la documentación y a las funciones que su rol tiene autorizadas para cada uno. | Al iniciar sesión solo aparecen los cursos asignados; leer o modificar un curso ajeno por API es denegado. | E3 · soporte por cursos | PR-D-01, S-04 | EP-03 · HU-09 / CU-09 |
| **RF-14** | Docente / Coordinación | Usuario autorizado registra o actualiza PDF procesable de ámbito permitido. | PDF válido se ingesta y es consultable; PDF incompatible devuelve error entendible y no altera corpus. | E2 · pipeline documental | PR-D-02 | EP-04 · HU-12 / CU-10 |
| **RF-15** | Docente / Coordinación | El sistema permite al responsable autorizado reemplazar un documento y mantener identificable su versión activa y la que respaldó cada cita. | Tras sustituir un documento, las consultas nuevas usan la versión activa; las citas existentes conservan referencia a la versión usada; una carga fallida no deja datos inconsistentes. | E2 · actualización documental | PR-D-03, PR-E-04 | EP-04 · HU-13 / CU-11 |
| **RF-16** | Docente / Coordinación | Usuario autorizado registra período/estado de vigencia de documentación institucional. | Respuesta sobre plazos históricos comunica período fuente; no afirma vigencia actual sin verificación. | E2 · vigencia documental | PR-D-03, PR-E-04 | EP-04 · HU-13 / CU-11 |
| **RF-17** | Docente | El docente consulta indicadores agregados y temas frecuentes de las preguntas correspondientes a sus cursos asignados. | Al seleccionar un curso propio se muestran totales, temas frecuentes y consultas sin respaldo de ese curso; no hay acceso a otros cursos ni se muestran datos personales. | E3 · extensión para docente (validar) | PR-D-04, S-02 | EP-05 · HU-16 / CU-12 |
| **RF-18** | Docente (consulta) / Responsable (gestiona) | El sistema mantiene un catálogo de cursos asociado a carreras y permite al docente localizar sus cursos asignados; quién crea o edita el catálogo se definirá institucionalmente. | Cada curso se vincula a una carrera; al consultar el catálogo un docente distingue sus cursos y puede filtrar documentación y métricas sin cruces entre cursos. | E3 · soporte de clasificación | C-01, PR-D-01 | EP-03 · HU-09/HU-10 / CU-02, CU-09, CU-13 |
| **RF-19** | Responsable autorizado (por definir) | Un responsable autorizado vincula docentes con cursos existentes siguiendo reglas de asignación validadas. | La asignación hace visible el curso al docente; retirar la asignación revoca acceso a documentos y métricas; otro curso permanece inaccesible. | E3 · soporte de permisos | C-01, PR-D-01, S-04 | EP-03 · HU-10 / CU-13 |
| **RF-20** | Coordinación | Actor autorizado incorpora y sustituye documentación general de la carrera. | Documento general válido pasa a búsqueda; operación ajena se rechaza; fuente queda identificada. | E2 · corpus institucional | PR-D-02, C-01 | EP-04 · HU-14 / CU-14 |
| **RF-21** | Coordinación | El coordinador autorizado consulta un panel que clasifica consultas, identifica preguntas frecuentes y señala brechas o preguntas sin respaldo documental, por ámbito académico autorizado. | Con consultas sintéticas conocidas, el panel muestra totales por ámbito, distribución de categorías, frecuencia de temas y casos sin respaldo; impide acceso no autorizado y no expone datos personales. | E3 · núcleo: panel coordinador | C-02, S-02 | EP-05 · HU-15 / CU-15 |
| **RF-22** | Administrador | Administrador habilita, edita y desactiva cuentas y permisos necesarios para V1. | Pruebas por rol y API verifican autorización y revocación de acceso. | E3 · soporte de seguridad | A-01, S-04 | EP-03 · HU-11 / CU-16 |
| **RF-28** | Estudiante | Cuando la consulta no pueda responderse con la documentación, el sistema informa la falta de respaldo y ofrece una derivación verificable a soporte humano autorizado. | Pregunta sin respaldo → abstención + orientación hacia canal institucional vigente verificado; no se inventan contactos ni se asegura una derivación automática no especificada. | E2 + E3 · derivación (descripción TT) | U-06 | EP-01 · HU-04 / CU-18, CU-03 |

## Requisitos no funcionales — candidatos (11)

| ID | Calidad | Condición candidata | Evidencia requerida / método | Validación |
|---|---|---|---|---|
| **RNF-01** | Fidelidad documental | Las afirmaciones normativas generadas estarán sustentadas por el corpus autorizado y su versión pertinente. | Evaluación RAGAS donde proceda + verificación humana de citas, evidencia y respuesta. | **Pendiente** |
| **RNF-02** | Abstención | El sistema no presentará una norma inventada cuando no existe evidencia suficiente. | Banco de preguntas respondibles, ambiguas y sin respuesta; comparar con referencias. | **Pendiente** |
| **RNF-03** | Autorización | Las rutas y acciones del API respetarán autenticación, rol y ámbitos autorizados. | Matriz rol×endpoint, pruebas 401/403 para carreras, cursos, documentos y conversaciones. | **Pendiente** |
| **RNF-04** | Privacidad / retención | Los datos de conversación y consultas analíticas tendrán finalidad, minimización, acceso y retención definidos. | Prueba con preguntas sintéticas que contienen correo/identificador; borrar hilo y comprobar efectos en mensajes/consultas. | **Pendiente** |
| **RNF-05** | Rendimiento | La consulta responderá en tiempos aceptables para el uso real bajo límites del proveedor. | Registrar tiempos de recuperación, LLM y total en repeticiones controladas. | **Pendiente** |
| **RNF-06** | Usabilidad | Los estudiantes realizarán las tareas principales sin asistencia del desarrollador. | Prueba de tareas reales + SUS con estudiantes; informar tamaño de muestra. | **Pendiente** |
| **RNF-07** | Accesibilidad | La interfaz permitirá recorrer las tareas principales con teclado y lectura comprensible. | Prueba manual de teclado, contraste y formularios. | **Pendiente** |
| **RNF-08** | Mantenibilidad | La actualización de documentación autorizada no requerirá modificar el código fuente para cada nuevo archivo. | Recorrido de carga de PDF, consulta y fallo/reintento. | **Pendiente** |
| **RNF-09** | Trazabilidad | Una respuesta respaldada permitirá identificar documento, página o sección y versión realmente utilizada. | Conjunto de respuestas verificadas; comprobación de versión activa e histórica. | **Pendiente** |
| **RNF-10** | Capacidad proporcional | La solución operará correctamente para el corpus y número de usuarios previstos en la tesis. | Prueba reproducible de carga e indexación a volumen acordado. | **Pendiente** |
| **RNF-11** | Resiliencia del proveedor | Cuando el LLM o la conexión fallen, el sistema informará claramente el estado sin aparentar una respuesta oficial verificada. | Simular timeout, cuota agotada, error HTTP y reinicio; comprobar respuesta y persistencia. | **Pendiente** |

## Contrato de aceptación del piloto (sin afirmar que se haya cumplido)

1. Autenticación y autorización: pruebas negativas contra /preguntar, historial, carrera, curso, documentos y métricas; ningún acceso fuera de ámbito.
2. Chat: al menos un caso respondible con cita de PDF/página y un caso no respondible con abstención y soporte humano verificado.
3. Fuente: el estudiante abre desde su chat la página de la versión documental usada sin transmitir credenciales por query string.
4. Documentos: PDF válido indexable, PDF ilegible rechazado, actualización preserva trazabilidad y el índice anterior si falla.
5. Coordinación: preguntas sintéticas permiten calcular conteos por tema y brechas, sin exposición de preguntas sensibles ni identificadores.
6. Evidencia académica E4: dataset oficial de referencia y piloto SUS con estudiantes reales; publicar el resultado **solo después** de ejecutarlos.

## Decisiones pendientes que impiden llamar a esta V1 «final aprobada»

- **P0:** definir normativa pública/restringida y autorización para cada rol y carrera/curso; el endpoint actual tenía consulta pública pese a propuesta de V1 autenticada.
- **P0:** decidir retención y anonimización de preguntas en `consultas`; hoy se conserva texto literal vinculado con `usuario_id`.
- **P0:** confirmar con coordinación indicadores útiles y método permitido para mostrar temas o brechas.
- **P1:** validar que los docentes necesitan RF-17 además del panel obligatorio del coordinador.
- **P1:** confirmar contacto real y mecanismo de derivación para RF-28; no codificar contactos supuestos.
- **P1:** pactar corpus vigente, benchmark, métricas, metas y muestra SUS.

## Alcance no incluido

RF-05/08/09/11 condicionados; RF-10/26 integrados; RF-23/24/25/27 fuera de V1 según matriz. Se pueden conservar componentes ya codificados como prototipo **sin presentarlos como compromiso validado**.

**Hoja oficial de trabajo:** https://docs.google.com/spreadsheets/d/1pPSQgj3N6TCjvd3Xrj-aF9uDtde05jFHmLjiDRpc3Sg/edit

**Repositorio:** https://github.com/AlexJavierQ/Tesis · Rama de estabilización: `chore/v1-tesis-revision-2026-11-11`.
