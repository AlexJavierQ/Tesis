# Modelo de datos V1: revisión crítica de la propuesta y decisiones

**Fecha:** 10/11/2026 · **Estado:** la propuesta se revisó y quedó **implementada
como esquema v6** en `nucleo/bd.py`, con migración aditiva probada. Sigue siendo
una V1 **no aprobada institucionalmente**.

El modelo vigente (diagrama ER, diccionario de datos, relaciones, reglas de
integridad y política de retención) está en [DISENO_BD.md](DISENO_BD.md). Este
documento registra **qué se propuso, qué se cambió al implementarlo y por qué**.

## 1. Criterio

El prototipo ya tenía un SQLite normalizado de 15 tablas y 19 claves foráneas
(esquema v5). No se reconstruyó: se conservaron las 15 tablas y se agregó solo
lo que exigen los requisitos de citación (RF-06, RF-12, RF-15, RNF-09) y de
privacidad de la analítica (RF-17, RF-21, RNF-04). **Modelo resultante: 17
tablas, 23 claves foráneas, 5 disparadores.** ChromaDB y los PDF siguen fuera de
SQLite.

## 2. `citas_mensaje`: ¿hacía falta una tabla?

**Problema real encontrado.** Las citas vivían solo en un JSON (`mensajes.citas`)
con `documento_id`, `version` y la **ruta del archivo** en el momento de
responder. Al subir una versión nueva, el archivo anterior se mueve a
`_versiones/` y la ruta original pasa a ser la de la versión nueva. El visor
abría la página por esa ruta: **una cita antigua mostraba la página de la versión
nueva**, no la que respaldó la respuesta. Además, nada impedía borrar un
documento citado.

**Alternativa más sencilla que se evaluó.** Conservar solo el JSON y resolver el
archivo en el servidor a partir de `(documento_id, version)`. Corrige el visor
sin tocar el esquema, pero deja dos huecos: el JSON no puede tener clave
foránea (una cita puede quedar apuntando a una versión borrada) y no se puede
consultar qué respuestas citan una versión.

**Decisión.** Se hicieron las dos cosas:

1. El visor pide la página por documento y versión
   (`GET /documentos/{id}/versiones/{numero}/paginas/{pagina}`); el cliente ya no
   envía ni recibe rutas de archivo.
2. Se creó `citas_mensaje` con clave foránea a `documento_versiones` y
   `ON DELETE RESTRICT`: la base impide borrar una versión citada, y la API
   responde 409 e indica desactivar el documento.

El JSON se sigue escribiendo como **copia de compatibilidad** (si hubiera que
volver al código v5, el historial seguiría mostrando sus citas). La lectura usa
`citas_mensaje`; el JSON solo se usa para mensajes antiguos sin fila normalizada.

**Diferencia con el borrador:** se quitó la columna `creado_en` (la fecha ya
está en `mensajes`).

## 3. `consulta_eventos`: analítica sin datos personales

**Problema real encontrado.** `consultas` guardaba la pregunta literal ligada a
`usuario_id`, y el panel mostraba preguntas textuales (temas agrupados por
significado y la lista de preguntas sin respaldo). Una pregunta puede contener
nombres, cédulas o situaciones personales; ocultar el usuario en la interfaz no
es anonimizar.

**Decisión.** La analítica se alimenta solo de `consulta_eventos`: carrera,
curso, modo, **categoría** de un vocabulario cerrado, si hubo respaldo, origen y
día. La tabla `consultas` queda como legado: no se escribe ni se lee, y no se
borra hasta que exista una política aprobada.

**Diferencias con el borrador, y por qué:**

| Borrador | Implementado | Motivo |
|---|---|---|
| `creado_en DATETIME` | `dia DATE` | Con la hora exacta, un evento podía cruzarse con `mensajes.creado_en` e identificar al autor. El panel solo necesita el día |
| (no existía) | `origen` ∈ {chat, migracion, sintetico} | Distinguir consultas reales de las derivadas de la migración y de los datos sintéticos de demostración; el panel avisa cuando hay sintéticos |
| Disparador curso-carrera solo en eventos | También en `documentos` y en `curso_docente` | La misma regla de integridad aplicaba al corpus y a la asignación de docentes |

**Clasificación.** Por palabras clave, determinística y sin modelo de lenguaje
(`nucleo/categorias.py`). Se prefirió a una clasificación con LLM porque es
explicable, repetible, gratuita y la pregunta no sale del proceso. Limitación
asumida: es una heurística cuya precisión no está evaluada; lo que no encaja cae
en `otros`.

**Qué se perdió a propósito.** La coordinación ya no ve el texto de las
preguntas sin respaldo; ve en qué categorías y ámbitos se concentran. Si la
institución necesita el texto, hay que definir consentimiento y retención antes
de volver a almacenarlo.

## 4. Lo que no se modeló

- **Matrícula estudiante ↔ curso.** No existe en el esquema ni hay fuente
  institucional para poblarla. El control de acceso V1 del estudiante es por
  carrera; cualquier estudiante de la carrera puede consultar desde cualquier
  curso de ella. Decisión pendiente con la coordinación.
- **Umbral mínimo de frecuencia** en los agregados (grupos pequeños). Queda
  documentado como riesgo residual en DISENO_BD.md §4.
- **Depuración de `consultas`.** Solo se documentan las dos opciones de SQL;
  ninguna se ejecuta automáticamente.

## 5. Migración ejecutada (v5 → v6)

| Fase | Estado | Evidencia |
|---|---|---|
| A. Respaldo de `sistema.db`, `chroma_db/` y `docs/` | Hecho | `datos/respaldos/2026-11-10_antes_v6/` |
| B. Ensayo en copia aislada | Hecho | 15 tablas idénticas fila a fila, `integrity_check = ok`, `foreign_key_check` vacío, repetible |
| C. Migración versionada en `bd.py` con respaldo automático | Hecho | `datos/respaldos/sistema_v5_<fecha>.db`; `PRAGMA user_version = 6` |
| D. Lectores y escritores sobre las tablas nuevas | Hecho | `historial.py`, `metricas.py`, `interfaces/api.py`, panel React |
| E. Pruebas | Hecho | `pruebas/test_v1_seguridad.py` (26 pruebas, incluye `PruebasMigracionV6`) |
| F. Política de retención de `consultas` y `logs` | **Pendiente** | Requiere decisión institucional |

El SQL de referencia de lo agregado está en
[sql/V1_EXTENSION_ESQUEMA_PROPUESTA.sql](sql/V1_EXTENSION_ESQUEMA_PROPUESTA.sql)
(se genera desde la base; la fuente de verdad es `nucleo/bd.py`).
