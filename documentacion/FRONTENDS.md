# Propuestas de interfaz

El backend expone una API REST. Las tres interfaces son **clientes intercambiables**:
ninguna contiene lógica del motor RAG, ninguna accede a ChromaDB ni al LLM, y
ninguna sabe de las otras. Todas hablan con los mismos endpoints HTTP.

Que existan tres implementaciones en tres tecnologías distintas, funcionando
sobre el mismo núcleo sin modificarlo, es la evidencia de que el desacoplamiento
es real y no una afirmación de diseño.

| | Propuesta 1 | Propuesta 2 | Propuesta 3 |
|---|---|---|---|
| **Interfaz** | Streamlit | React + Vite | Widget embebible |
| **Carpeta** | `app.py` | `web/` | `widget/` |
| **Lenguaje** | Python | JavaScript (JSX) | JavaScript (sin build) |
| **Dependencias** | Streamlit | React, Vite | ninguna |
| **Compilación** | no | sí (`npm run build`) | no |
| **Alojamiento** | Streamlit Cloud | Vercel / estático | cualquier servidor web |
| **Integrable en un portal** | no | parcialmente (iframe) | sí, con una etiqueta |
| **Arranque** | `streamlit run app.py` | `npm run dev` | abrir `index.html` |

## Propuesta 1 — Streamlit

La interfaz original del MVP. Todo en Python, sin tocar JavaScript.

**Cuándo conviene:** prototipado y validación rápida con la coordinación. Permite
enseñar el flujo completo sin infraestructura de frontend.

**Limitaciones:** no se integra en un portal existente, el aspecto está atado a
los componentes de Streamlit, y cada interacción recarga el script completo.

## Propuesta 2 — React + Vite

La interfaz de referencia para producción.

**Cuándo conviene:** despliegue institucional con identidad visual propia,
control total sobre la experiencia y posibilidad de crecer (rutas, estado,
autenticación cuando exista).

**Limitaciones:** requiere Node y un paso de compilación; es una aplicación
aparte del portal, no algo que se inserte en él.

## Propuesta 3 — Widget embebible

HTML, CSS y JavaScript puro en un solo archivo, sin build ni dependencias. Se
integra en cualquier página con una línea:

```html
<script src="asistente-widget.js" data-api="http://localhost:8000"
        data-carrera="computacion"></script>
```

Usa **Shadow DOM** con `all: initial`, de modo que los estilos del portal
anfitrión no lo alteran ni él altera el portal. La página de demostración
(`widget/index.html`) incluye deliberadamente una regla CSS hostil para que ese
aislamiento sea comprobable en vivo.

**Cuándo conviene:** integrarlo en el portal que la universidad ya tiene, sin
pedir al equipo de sistemas que adopte un framework ni que monte un pipeline de
build.

**Limitaciones:** sin build no hay optimizaciones ni división de código; crecer
mucho lo haría difícil de mantener. Es una interfaz de consulta, no una
aplicación completa.

## Nota de despliegue

El backend en Python necesita un servidor persistente: **no corre en Vercel**.
Vercel u otro estático sirve el frontend (propuestas 2 y 3); la API vive en un
servicio con proceso permanente.

## CORS

La API solo acepta los orígenes declarados en la variable `CORS_ORIGINS`
(por defecto `http://localhost:5173`). Al servir el widget o el React desde otro
origen hay que incluirlo:

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:5500 uvicorn api:app --reload
```

Es el fallo más probable al montar una demostración.
