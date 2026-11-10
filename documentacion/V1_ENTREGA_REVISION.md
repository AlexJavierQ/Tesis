# V1 para la revisión del 11/11/2026: qué se entregó y cómo se comprobó

**Rama:** `chore/v1-tesis-revision-2026-11-11` · **Corte:** 10/11/2026 ·
**Esquema de datos:** v6 (17 tablas).

Esta V1 es una **propuesta técnica**: los 18 requisitos funcionales no están
aprobados institucionalmente. Aquí no hay resultados de entrevistas, de
evaluación con estudiantes ni de calidad de respuestas: solo lo que se ejecutó y
se puede repetir con los comandos indicados.

## 1. Qué se corrigió

| Prioridad | Problema encontrado | Corrección | Dónde |
|---|---|---|---|
| P0 Citas | La cita guardaba la **ruta** del PDF. Al subir una versión nueva, la ruta pasa a la versión nueva: una cita antigua abría la página equivocada | El visor pide la página por documento y versión, y el servidor busca el archivo de esa versión. Nueva tabla `citas_mensaje` con clave foránea a la versión exacta | `interfaces/api.py`, `nucleo/historial.py`, `Chat.jsx` |
| P0 Citas | Se podía borrar un documento citado y dejar la cita rota | La base lo impide (RESTRICT) y la API responde 409 indicando desactivarlo | `nucleo/ingest.py`, `nucleo/bd.py` |
| P0 Privacidad | Cada consulta guardaba la pregunta literal ligada al usuario, y el panel mostraba preguntas textuales | Analítica minimizada en `consulta_eventos`: solo categoría, respaldo y día. La tabla `consultas` queda como legado sin uso | `nucleo/metricas.py`, `nucleo/categorias.py`, `Metricas.jsx` |
| P0 Autorización | `/facultades`, `/carreras` y los cursos de una carrera eran públicos | Exigen sesión; cada rol ve solo su ámbito | `interfaces/api.py` |
| P0 Autorización | `/preguntar` validaba que la carrera existiera **antes** de pedir sesión (permitía enumerar carreras sin login) | La sesión y la carrera se validan primero | `interfaces/api.py` |
| P0 Autorización | Un docente podía abrir páginas de documentos de cursos ajenos de su carrera | Lectura limitada a sus cursos asignados | `interfaces/api.py` |
| P0 Autorización | La coordinación podía borrar, desactivar o cambiar la contraseña de un usuario que también pertenece a otra carrera, y al editar sus carreras le quitaba las ajenas | Solo puede cambiar su pertenencia a las carreras propias; lo ajeno se conserva | `interfaces/api.py` |
| P0 Coherencia | Docente y coordinación tenían "Chat" como primera pantalla, pero la API solo lo permite al estudiante (pantalla rota al entrar) | El chat queda solo en el menú del estudiante; solo el estudiante crea conversaciones | `navegacion.js`, `interfaces/api.py` |
| P0 Integridad | Nada en la base impedía un documento con un curso de otra carrera, ni asignar a un curso a quien no es docente de su carrera. Un docente conservaba cursos de una carrera que se le retiraba | 5 disparadores y limpieza al cambiar de carreras | `nucleo/bd.py`, `nucleo/auth.py` |
| P1 Analítica | Los saludos ("hola", "gracias") contaban como consultas con respaldo | No se registran | `nucleo/rag.py`, `interfaces/api.py` |
| P1 Pruebas | Las pruebas importaban la API sobre la base real | Carpeta de datos temporal (`PRACTICUM_DATOS`) | `nucleo/config.py`, `pruebas/aislado.py` |

No se agregaron funciones nuevas fuera de los requisitos. Se retiró el
agrupamiento de preguntas "por significado" del panel, porque exigía guardar y
mostrar las preguntas literales.

## 2. Resultados de pruebas

Ejecutadas el 10/11/2026 en Windows 11, Python 3.14.5, Node 24.11.1, con el
corpus oficial (2 PDF, 204 fragmentos) y la clave de Groq configurada.

### Superadas

| # | Comando | Resultado |
|---|---|---|
| 1 | `python -m unittest pruebas.test_v1_consulta -v` | **4 de 4** OK |
| 2 | `python -m unittest pruebas.test_v1_seguridad -v` | **26 de 26** OK (11 s) |
| 3 | `python -m unittest pruebas.test_v1_consulta pruebas.test_v1_seguridad` | **30 de 30** OK en un mismo proceso |
| 4 | `python verificar.py` | **9 de 9** pasos OK (esquema v6, 17 tablas, FK íntegras, búsqueda híbrida, abstención, respuesta con cita en pág. 24 v1, analítica sin pregunta ni usuario) |
| 5 | `python -m pruebas.integridad` | **26 de 26** comprobaciones OK (PDF sin texto, versionado, restaurar, activar/desactivar, fallo a mitad de subida, permisos, citas por versión, limpieza) |
| 6 | `npm ci` (en `interfaces/react`) | OK, 71 paquetes |
| 7 | `npm run build` (en `interfaces/react`) | OK, 1957 módulos |

Las pruebas 1 a 3 corren en una carpeta temporal con datos sintéticos y **sin
modelo de lenguaje** (el motor RAG y el índice vectorial se sustituyen): prueban
la API, los permisos y la base. Las pruebas 4 y 5 usan el corpus, el índice y el
modelo reales.

Qué cubren las 26 pruebas nuevas (`pruebas/test_v1_seguridad.py`):

| Clase | Pruebas | Qué comprueba |
|---|---|---|
| `PruebasAutorizacion` | 12 | 401 sin sesión en 15 rutas; el token en la URL no sirve; estudiante solo en su carrera; solo el estudiante pregunta; conversación ajena inaccesible; docente solo en sus cursos; subida de PDF válido e inválido; coordinación no sale de su carrera; usuario compartido entre carreras; administrador sin documentos ni métricas; retirar la asignación revoca el acceso; desactivar la cuenta cierra la sesión |
| `PruebasCitas` | 3 | Cita enlazada a la versión por clave foránea; página visible solo con permiso; **la cita antigua sigue abriendo la v1 después de publicar la v2**; no se borra un documento citado |
| `PruebasAnalitica` | 6 | Conteos por categoría, brechas y ámbitos con 7 consultas conocidas; una pregunta con nombre, cédula y correo no aparece en el panel ni en la tabla; cada rol ve solo su ámbito; los saludos no cuentan; borrar el historial no altera los agregados; vocabulario cerrado |
| `PruebasIntegridad` | 4 | Disparadores curso-carrera; solo docentes de la carrera; cambio de carrera o rol retira cursos; unicidad y claves foráneas; 17 tablas |
| `PruebasMigracionV6` | 1 | Base v5 sintética → v6: respaldo previo, tablas anteriores idénticas, citas y eventos derivados, repetible |

### Comprobado a mano en el navegador (10/11/2026)

Con `python arrancar.py` y las cuentas de demostración: los tres recorridos de
la sección 4 (estudiante con cita y abstención, docente, coordinación). La
petición de la página citada fue
`GET /documentos/1/versiones/1/paginas/24` con el token en el encabezado.

### Fallidas

Ninguna en la ejecución final. Durante el desarrollo fallaron 2 de las pruebas
nuevas por datos mal construidos en la propia prueba (un PDF sintético cuyo
texto no cabía en la página y el nombre de la facultad sembrada); se corrigió la
prueba, no el sistema.

### No ejecutadas (no afirmar que se cumplen)

- Evaluación de fidelidad de las respuestas (RAGAS o revisión humana): RNF-01.
- Banco de preguntas respondibles, ambiguas y sin respuesta: RF-07, RNF-02.
  Solo se verificaron casos sueltos.
- Usabilidad con estudiantes (SUS): RNF-06. Accesibilidad con teclado y lector
  de pantalla: RNF-07.
- Carga, concurrencia y volumen: RNF-10. Tiempos en condiciones controladas:
  RNF-05 (solo hay mediciones puntuales, ver sección 3).
- Simulación de fallos del proveedor (timeout, cuota, error HTTP): RNF-11. El
  modo degradado se observó una vez, al superar el límite por minuto de Groq.
- Subida de PDF **desde la interfaz** del docente (se probó por API, que es lo
  que la interfaz llama).
- Precisión del clasificador de categorías.
- `npm audit` informa 6 vulnerabilidades (2 moderadas, 4 altas) en dependencias
  de desarrollo del frontend; no se revisaron ni se actualizaron.

## 3. Requisitos: implementados, parciales y pendientes

"Implementado" significa que el comportamiento existe y tiene una comprobación
que se puede repetir. No significa validado por la institución.

### Funcionales

| ID | Estado | Evidencia y límites |
|---|---|---|
| RF-01 | Implementado | Login por usuario o correo; credenciales inválidas rechazadas; historial ajeno 403 (`PruebasAutorizacion`, `verificar.py` paso 5) |
| RF-02 | Implementado | La carrera se valida en el servidor; carrera ajena 403 sin invocar el motor |
| RF-03 | Implementado | Respuesta fundamentada con cita (`verificar.py` paso 8; navegador) |
| RF-04 | Implementado, con un límite | El estudiante elige "general", "general + curso" o "solo el curso". **No hay matrícula estudiante-curso**: puede consultar cualquier curso de su carrera |
| RF-06 | Implementado | Cada cita trae documento, página, sección y versión; se coteja la pág. 24 de la versión 1 |
| RF-07 | Implementado; evaluación pendiente | Dos capas: umbral de similitud y abstención del modelo. Verificado con casos sueltos, no con un banco de preguntas |
| RF-12 | Implementado | Visor de la página citada, con permiso y versión exacta (`PruebasCitas`) |
| RF-13 | Implementado | El docente ve y gestiona solo sus cursos; lo ajeno responde 403 |
| RF-14 | Implementado | PDF válido se indexa; PDF sin texto o dañado se rechaza sin dejar rastro (`pruebas.integridad` 1 y 5) |
| RF-15 | Implementado | Versionado, restauración y cita histórica que conserva su versión |
| RF-16 | Implementado; comportamiento del modelo no evaluado formalmente | Campo de vigencia por documento; en la prueba manual el asistente indicó el período histórico y recomendó confirmar |
| RF-17 | Implementado (**extensión por validar**) | Panel del docente por curso asignado, solo agregados |
| RF-18 | Implementado | Cursos ligados a carreras; el docente distingue los suyos |
| RF-19 | Implementado | La coordinación asigna docentes; retirar la asignación revoca el acceso. Quién debe ser el responsable está por definir |
| RF-20 | Implementado | La coordinación gestiona la normativa general de sus carreras; lo ajeno 403 |
| RF-21 | Implementado; contenido por validar | Totales por ámbito, categorías, brechas y consultas sin respaldo. **No muestra preguntas literales** (decisión de privacidad): "preguntas frecuentes" se interpreta como "categorías frecuentes" |
| RF-22 | Implementado | Alta, edición y desactivación de cuentas; la desactivación cierra sesiones |
| RF-28 | **Parcial** | Abstención con orientación genérica ("consultar con la coordinación"). Falta el canal institucional verificado; no se inventó ningún contacto |

### No funcionales

| ID | Estado | Evidencia y límites |
|---|---|---|
| RNF-01 Fidelidad | **Pendiente** | Sin evaluación |
| RNF-02 Abstención | Parcial | Mecanismo implementado; falta el banco de preguntas |
| RNF-03 Autorización | Implementado y probado | Pruebas 401/403 por rol, carrera, curso, documento y conversación |
| RNF-04 Privacidad y retención | Parcial | Minimización implementada y probada. Falta aprobar la retención de `logs` y de la tabla legado `consultas` |
| RNF-05 Rendimiento | Parcial | Mediciones puntuales en esta máquina: abstención por umbral 0,1 s; respuesta con modelo 1,2 a 1,8 s; primera respuesta tras arrancar, unos 15 s por la carga del modelo de embeddings. No es una prueba controlada |
| RNF-06 Usabilidad | **Pendiente** | Requiere estudiantes reales |
| RNF-07 Accesibilidad | **Pendiente** | No evaluada |
| RNF-08 Mantenibilidad | Implementado | Subir o reemplazar un PDF no requiere tocar código |
| RNF-09 Trazabilidad | Implementado y probado | Documento, página, sección y versión, con clave foránea |
| RNF-10 Capacidad | **Pendiente** | Sin prueba de volumen |
| RNF-11 Resiliencia | Parcial | Modo degradado existente y observado; sin pruebas automáticas de fallo |

## 4. Guion de demostración (5 a 7 minutos)

### Preparación (antes de la reunión)

```bash
python -m pruebas.datos_demo     # datos sintéticos (repetible)
python arrancar.py               # API en :8000 y React en :5173
```

1. Abre `http://localhost:5173` y haz **una pregunta de calentamiento** como
   estudiante: la primera tarda unos 15 s porque carga el modelo de embeddings.
   Después borra esa conversación.
2. Deja **unos 30 segundos entre preguntas**. La cuenta gratuita de Groq tiene un
   límite por minuto; si se supera, el asistente responde en modo degradado
   (muestra los fragmentos con un aviso). Si ocurre en vivo, es el
   comportamiento previsto de RNF-11: se explica y se repite la pregunta.
3. No ejecutes `verificar.py` ni `pruebas.integridad` justo antes: consumen cuota.

Cuentas (todas con contraseña `demo2026`; son de prueba local):

| Usuario | Rol | Ámbito |
|---|---|---|
| `estudiante` | Estudiante | Computación |
| `docente` | Docente | Computación, curso Practicum 2 |
| `docente2` | Docente | Computación, curso Practicum 3 (sintético) |
| `coord` | Coordinación | Computación |
| `coord2` | Coordinación | Electrónica (carrera sintética) |
| `estudiante2` | Estudiante | Electrónica (carrera sintética, sin documentos) |
| `admin` | Administrador | Sistema |

### Recorrido

| Minuto | Quién | Qué hacer | Qué decir |
|---|---|---|---|
| 0:00 | (introducción) | Mostrar el login | "V1 propuesta: chat estudiantil con citas y panel analítico de coordinación. Todo exige sesión y el servidor valida carrera y curso." |
| 0:30 | `estudiante` | Con "Reglamento general", preguntar: **¿El prácticum tiene evaluación de recuperación?** | "Responde solo con la normativa oficial y cita documento, página y versión." |
| 1:15 | `estudiante` | Pulsar la cita **pág. 24** | "Abre la página exacta, sección 13.2, de la versión 1. Si mañana se publica la versión 2, esta cita sigue abriendo la 1." |
| 1:45 | `estudiante` | Mover el deslizador a **General + curso**, curso Practicum 2, y preguntar: **¿Hasta cuándo puedo postular a una plaza de prácticas?** | "El dato sale del material del curso, que es del período abril-agosto 2024: el asistente lo dice y recomienda confirmar. No presenta un plazo histórico como actual." |
| 2:30 | `estudiante` | Preguntar: **¿Cuánto cuesta el parqueadero del campus?** | "No hay respaldo: se abstiene y orienta a la coordinación. No inventa." |
| 3:00 | `docente` | Entrar. Se abre **Documentos** | "Solo ve Practicum 2, su curso asignado. Practicum 3 es de otro docente y por API recibe 403." |
| 3:30 | `docente` | **Subir PDF**: volver a subir `Practicum2_Entorno_Laboral_2024.pdf` (está en `datos/docs/computacion/cursos/Practicum 2/`) | "Queda como versión 2, con sus fragmentos indexados; la anterior se conserva. Un PDF escaneado se rechaza." |
| 4:00 | `docente` | Abrir **Análisis de consultas** | "Solo agregados de su curso. Esto es una extensión que aún debo validar con los docentes." |
| 4:30 | `coord` | Entrar. Se abre **Análisis de consultas** | "Panel de coordinación: totales, categorías más consultadas, brechas documentales y reparto por ámbito. Los datos son sintéticos y el panel lo avisa." |
| 5:15 | `coord` | Cambiar el ámbito a **Practicum 3** | "Aquí todas las consultas quedaron sin respaldo: ese curso no tiene documentos. Es una brecha documental." |
| 5:45 | `coord2` | Entrar | "La coordinación de otra carrera solo ve la suya; pedir los datos de Computación devuelve 403." |
| 6:15 | (cierre) | Mostrar `documentacion/modelo_bd_sql.png` | "17 tablas. Dos nuevas: citas enlazadas a la versión exacta y analítica sin preguntas ni usuarios. 30 pruebas automáticas. Lo pendiente: evaluación de calidad, usabilidad y validación institucional." |

Otras preguntas comprobadas con el corpus (por si preguntan):

- ¿Cuántas horas de prácticas tiene una carrera de ingeniería? (cita pág. 10)
- ¿Qué evidencias se presentan en las prácticas de entorno laboral? (cita pág. 25)
- ¿Cómo se pondera la evaluación del prácticum? (cita pág. 24)
- "Solo el curso", Practicum 2: ¿Cuáles son las fases de las prácticas en el entorno laboral? (cita pág. 8)
- ¿Quién es el decano de la facultad? (se abstiene)

Después de la demostración: `python -m pruebas.datos_demo --quitar` retira los
datos sintéticos. Si subiste la versión 2 del PDF del curso, puedes dejarla (es
el mismo contenido) o restaurar la versión 1 desde **Versiones**.

## 5. Qué consultar con la ingeniera

1. **Alcance del panel docente (RF-17).** El objetivo E3 exige el chat y el panel
   del coordinador. ¿El panel del docente entra en la V1 o se deja como trabajo
   futuro?
2. **Analítica sin preguntas literales (RF-21, RNF-04).** El panel muestra
   categorías y brechas, no el texto de las preguntas. ¿Es suficiente para la
   coordinación, o necesitan ver las preguntas sin respaldo? En ese caso, ¿qué
   consentimiento y qué retención se exigirían?
3. **Categorías.** ¿Son adecuadas las siete (horas, plazos, formatos, evaluación,
   requisitos, trámites, otros)? ¿Quién las valida?
4. **Acceso del estudiante por curso (RF-04).** Hoy basta pertenecer a la
   carrera. ¿Hace falta matrícula por curso? ¿De dónde saldría ese dato?
5. **Derivación a soporte humano (RF-28).** ¿Cuál es el canal institucional
   vigente que debe mostrar la abstención?
6. **Quién asigna docentes y crea cursos (RF-18, RF-19).** Hoy lo hace la
   coordinación de la carrera. ¿Es el actor correcto?
7. **Retención.** ¿Cuánto tiempo se conservan las conversaciones y la bitácora?
   ¿Se depura la tabla antigua `consultas`, que aún tiene preguntas literales?
8. **Evaluación (E4).** Corpus vigente, banco de preguntas de referencia,
   métricas y metas, y tamaño de la muestra para SUS.
9. **Chat sin login (widget).** Quedó fuera de la V1. ¿Se confirma?

## 6. Límites conocidos de esta V1

- Piloto controlado: una carrera con corpus real (Computación), dos PDF.
- El control de acceso del estudiante es por carrera, no por curso.
- En ámbitos con muy pocos estudiantes, un agregado pequeño podría atribuirse a
  una persona; el umbral mínimo de frecuencia no está implementado.
- La tabla legado `consultas` conserva las preguntas literales de la v5 hasta
  que se apruebe su depuración. Ninguna ruta la lee.
- El mensaje de abstención es configurable por el administrador; el texto actual
  no nombra un canal concreto.
- Depende de un proveedor externo gratuito (Groq) con límites por minuto.
