# Widget embebible — Asistente de Prácticum

Tercera propuesta de frontend del MVP, junto a `app.py` (Streamlit) y `web/` (React + Vite).
Las tres consumen **la misma API REST de FastAPI** y ninguna toca el núcleo (`rag.py`,
`ingest.py`, `llm.py`). Esa es la tesis que este directorio demuestra: si el mismo backend
soporta Python, React y JavaScript puro sin una sola modificación, el desacoplamiento es real
y no una intención de diseño.

## Qué es

Un chat flotante que se **incrusta en el portal que el estudiante ya usa**, en lugar de pedirle
que visite otra aplicación. Un único archivo de ~700 líneas: HTML, CSS y JavaScript puro.

- **Sin build.** No hay `npm install`, ni `package.json`, ni paso de compilación.
- **Sin dependencias ni CDN.** Se copia a cualquier servidor estático y funciona. La única red
  que necesita es la de la propia API.
- **Sin framework.** DOM nativo, `fetch` nativo, `<img>` nativo.

## Integración

Una sola línea, al final del `<body>` del portal:

```html
<script src="/js/asistente-widget.js" data-api="https://api.utpl.edu.ec" data-carrera="computacion" defer></script>
```

| Atributo       | Obligatorio | Por defecto             | Descripción                                   |
|----------------|-------------|-------------------------|-----------------------------------------------|
| `data-api`     | recomendado | `http://localhost:8000` | URL base de la API REST                       |
| `data-carrera` | no          | `computacion`           | Carrera sobre la que se consulta              |
| `data-curso`   | no          | *(ninguno)*             | Restringe el alcance a un curso concreto      |

La configuración va en atributos `data-*` para que el integrador del portal no tenga que
escribir JavaScript: solo HTML. Es el mismo patrón de los widgets de analítica o de soporte.

## Probarlo

1. Levantar la API desde la raíz del proyecto:
   ```
   uvicorn api:app --reload
   ```
2. Servir esta carpeta (el widget necesita `http://`, no `file://`, por CORS):
   ```
   python -m http.server 5500 --directory widget
   ```
3. Abrir `http://localhost:5500/`.

**CORS:** la API solo acepta los orígenes de `CORS_ORIGINS` (por defecto, el puerto de Vite).
Para probar el widget hay que incluir su origen:

```
set CORS_ORIGINS=http://localhost:5173,http://localhost:5500
```

`index.html` simula un portal universitario con contenido de relleno. Su CSS incluye a propósito
reglas hostiles (`button { background: red !important; font-family: Comic Sans }`) del tipo que
suele haber en un portal heredado: si el widget se sigue viendo correcto, el aislamiento
funciona.

## Decisiones de diseño

### Shadow DOM

Es la decisión central. El widget se inyecta en una página ajena y desconocida, con su propio
CSS. El shadow root levanta una frontera de estilos en los dos sentidos:

- **Hacia dentro:** el CSS del portal no alcanza los nodos del widget, así que el asistente se
  ve igual en cualquier sitio.
- **Hacia fuera:** las reglas del widget no se filtran al portal, así que integrarlo no puede
  romper la maquetación existente.

Es la alternativa honesta al `<iframe>`: el mismo aislamiento visual, pero sin un segundo
documento, sin problemas de altura y con acceso directo al DOM. A esto se le suma `all: initial`
en `:host`, porque el Shadow DOM bloquea los selectores externos pero **no** la herencia de
propiedades como `font`, `color` o `line-height`.

### Verificabilidad

Cada respuesta muestra sus citas como botones. Al pulsarlos se abre un visor con la página
exacta del documento, servida ya rasterizada en PNG por
`GET /documentos/pagina`; navegable con `GET /documentos/info`. No hace falta ningún lector de
PDF en el cliente. Es la misma garantía que ofrecen los otros dos frontends: el estudiante
comprueba la fuente sin salir de donde está.

Cuando `con_respaldo` es `false`, se muestra un aviso destacado de derivación a coordinación. El
asistente no debe aparentar una autoridad documental que no tiene.

### Seguridad y robustez

- Todo el contenido que viene de la API se inserta con `textContent`, nunca con `innerHTML`: el
  texto del modelo y los nombres de documento son datos externos.
- Todo el código vive en una IIFE; no publica ni una variable global.
- Los fallos de red se muestran como un mensaje dentro del chat y la conversación sigue viva. Un
  widget incrustado nunca debe propagar sus errores al portal anfitrión.

### Accesibilidad

Navegación completa por teclado, `Escape` cierra la capa más interna primero (visor antes que
panel), foco devuelto al disparador al cerrar, `role="log"` con `aria-live="polite"` para la
conversación, `aria-expanded`/`aria-controls` en el lanzador, foco visible en color acento y
`prefers-reduced-motion` respetado.

### Móvil

Por debajo de 560 px el panel pasa a pantalla completa: en un teléfono, una ventana flotante
deja el teclado virtual encima del texto. El `textarea` usa 16 px reales porque por debajo de
ese tamaño iOS hace zoom automático al enfocar.

## Cuándo conviene cada frontend

| | Streamlit (`app.py`) | React (`web/`) | Widget (`widget/`) |
|---|---|---|---|
| **Público** | Coordinación, tribunal | Estudiantes y docentes | Estudiantes en el portal |
| **Fuerte en** | Prototipar y demostrar rápido | Aplicación completa con gestión documental y métricas | Adopción: llega donde el usuario ya está |
| **Coste de integración** | Servidor Python aparte | Build y despliegue estático | Una etiqueta `<script>` |
| **Elegir cuando** | Se necesita iterar en horas | Se necesita una app propia y mantenible | El portal institucional ya existe y no se quiere migrar |

El argumento del widget no es técnico sino de adopción: la barrera más alta de un asistente
universitario no es construirlo, es que el estudiante recuerde ir a él. Un widget elimina esa
barrera a cambio de renunciar a funcionalidad.

## Limitaciones

Son deliberadas y conviene declararlas:

- **Solo consulta.** No incluye subida de documentos, gestión de cursos ni métricas: eso vive en
  React y Streamlit. El widget hace una cosa.
- **Sin autenticación.** El sistema aún no la tiene. Cualquier visitante del portal puede
  preguntar. Antes de producción hay que añadir autenticación en la API, no en el cliente.
- **Sin historial persistente.** La conversación se pierde al recargar; no hay almacenamiento
  local ni de sesión.
- **Sin pruebas automatizadas ni tipado.** Al no haber build tampoco hay linter, transpilación
  ni *tree-shaking*. Es el precio de la simplicidad, y por eso se compensa con comentarios
  extensos: el archivo se lee entero.
- **Depende de CORS.** Al vivir en otro origen que la API, requiere que el backend liste el
  dominio del portal.
- **Navegadores modernos.** Usa Shadow DOM, `fetch` y `URLSearchParams`. Sin soporte para
  Internet Explorer.
