# Lineamientos para los documentos que ingresan al sistema

Este documento define **qué requisitos debe cumplir un PDF** para que el
asistente pueda responder sobre él con calidad. Está pensado para que la
coordinación de la carrera y los docentes sepan qué subir y cómo prepararlo.

Se apoya en el material real que la Dirección General de Vinculación con
la Sociedad (DGVS) utiliza para las prácticas preprofesionales (documento
de referencia: *"Capacitación Prácticas Preprofesionales – Entorno
Laboral, abril–agosto 2024"*, DGVS).

---

## 1. Requisitos mínimos (obligatorios)

Un documento **no será aceptado por el sistema** —o dará respuestas
pobres— si no cumple esto:

| # | Requisito | Motivo |
|---|---|---|
| R1 | Formato **PDF** (`.pdf`) | Único formato que la ingesta procesa. |
| R2 | Texto **seleccionable** (no imagen) | El sistema no aplica OCR (ver `ALCANCES.md` §3.1). Verifica con el script `revisar_pdf.py`. |
| R3 | Idioma **español** | El corpus, los usuarios y la evaluación son en español. |
| R4 | Tamaño **≤ 20 MB** | Archivos más grandes tardan minutos en indexar y saturan la BD vectorial. |
| R5 | Nombre del archivo **sin caracteres especiales** ni espacios (usa `_`) | Evita problemas al servir el PDF desde el visor de citas. Ej: `Reglamento_Practicum_2026.pdf`. |
| R6 | Contenido **normativo o informativo institucional** | Fuera de eso, el sistema no debería responder (ver ámbito). |

### Cómo verificar R2 rápidamente

Abre el PDF, intenta **seleccionar una frase con el mouse**. Si puedes
copiarla al portapapeles, es texto seleccionable. Si el cursor pasa por
encima sin resaltar nada, es imagen y no sirve.

También puedes correr:

```bash
python revisar_pdf.py "ruta/al/documento.pdf"
```

El script te dirá cuántas páginas tienen texto útil, cuántas están vacías
y una estimación de si el documento es apto.

---

## 2. Estructura recomendada

Cuanto más se parezca el PDF a estas convenciones, mejor responderá el
sistema (recall más alto y citas más precisas).

### 2.1 Portada con metadatos

Primera página con:

- **Título del documento** en fuente grande (p. ej. *"Reglamento de
  Prácticum – Carrera de Computación"*).
- **Autoridad emisora** (Dirección, Facultad, Consejo).
- **Fecha de vigencia** (mes y año o fecha exacta).
- **Versión** si aplica (v1.0, v2024-abril).

Ejemplo real:

> DIRECCIÓN GENERAL DE VINCULACIÓN CON LA SOCIEDAD
> Capacitación Prácticas Preprofesionales – Entorno Laboral
> Abril – Agosto 2024

### 2.2 Secciones numeradas o con títulos claros

Cada sección con un encabezado en **una línea propia**. Ejemplos válidos:

- `Artículo 1. Objeto` · `Artículo 2. Ámbito de aplicación`
- `TÍTULO I – Disposiciones generales`
- `1. Definiciones` · `2. Actores` · `3. Procesos`

El indexador ya prefiere partir por unidades semánticas (artículos,
títulos, capítulos, secciones numeradas). Cuanto más regular sea la
numeración, mejor.

### 2.3 Definiciones formales explícitas

Cada término se define en **una frase que empieza con el sujeto**:

> El practicante es el estudiante que realiza su práctica preprofesional
> con fines educativos como parte de su proceso de formación académica…

Esto se recupera muy bien porque el nombre del concepto está al inicio
del párrafo.

### 2.4 Listas para enumerar responsabilidades

Cada elemento en un ítem propio, con la responsabilidad expresada de
forma **autocontenida** (que se entienda sin ver el resto de la lista):

> a. Realizar las actividades académicas y formativas en la organización
> receptora.
> b. Cumplir con los horarios establecidos y el número de horas para las
> prácticas preprofesionales.

Evita ítems tipo *"Lo mismo pero al final"* o *"Ver punto anterior"*, que
al recuperarse aislados quedan sin sentido.

### 2.5 Tablas simples

Las tablas SÍ se procesan, pero deben ser **de una fila por concepto**:

| Estado | Descripción |
|---|---|
| Registrada | El estudiante ha registrado una postulación… |
| Tramitar convenio | El equipo de la DGVS inicia el acercamiento… |

Evita celdas combinadas, tablas anidadas, o tablas donde una fila
depende visualmente de otra.

### 2.6 Cifras y plazos siempre con contexto

En vez de una celda suelta con `"96 horas"`, escribe:
> Prácticum 1: **96 horas** de observación y diagnóstico.

Esto es CRÍTICO. El sistema recupera fragmentos, no celdas. Un número
suelto sin el concepto al que se refiere no puede sostener una respuesta.

---

## 3. Buenas prácticas (haz esto)

- **Un tema por sección.** Si una sección mezcla horas, plazos, formatos
  y notas, al recuperarla el modelo tiene menos foco.
- **Cita las normas externas.** *"Según el Art. 26 del Reglamento de
  Régimen Académico Interno…"*. Da trazabilidad institucional.
- **Fechas absolutas.** *"Hasta el 03 de mayo de 2024"* en vez de *"esta
  semana"*.
- **Nombres completos de actores.** *"Tutor académico"* en vez de solo
  *"el docente"*.
- **Glosario al final** si hay siglas (DGVS, CES, IESS…).
- **Índice al inicio** con los títulos de sección: ayuda a la lectura
  humana y no estorba al indexador.

---

## 4. Malas prácticas (evita esto)

Estos patrones aparecen en el material real y producen respuestas pobres:

### 4.1 Slides que son solo un diagrama o flujo
El PDF de referencia tiene páginas con solo un título (`"Procesos
generales"`, `"Registro de evidencias docente"`) y el resto es una imagen
del flujo. El sistema **no lee esas imágenes**.

**Cómo arreglarlo:** después del diagrama, añade un **párrafo escrito**
que resuma el flujo en texto ("El proceso consta de 4 pasos: 1) el
estudiante registra su postulación… 2) el docente valida…").

### 4.2 Repetir el mismo texto de pie de página en cada slide
Frases como *"Agregue un pie de página"* o *"FR"* aparecen en varias
páginas del PDF de referencia y compiten en la recuperación.

**Cómo arreglarlo:** el sistema tiene un filtro (`limpiar_ruido`) que
elimina avisos genéricos, pero cuanto menos ruido tenga el PDF de origen,
mejor.

### 4.3 Texto en imágenes (capturas de pantalla del portal)
Las páginas 11-17 del PDF de referencia muestran capturas del portal
sin texto extraíble.

**Cómo arreglarlo:** cada captura debe ir **acompañada de una lista o
párrafo** que describa lo que se ve, con las palabras clave que un
estudiante buscaría.

### 4.4 PDFs escaneados
Cualquier PDF que provenga de un escáner (aunque parezca legible) no
tiene texto seleccionable.

**Cómo arreglarlo:** exportar desde el archivo original (Word, PPT,
Google Docs) usando *"Guardar como PDF"* o *"Imprimir → PDF"*. **No**
escanear.

### 4.5 Nombres de archivo caóticos
`"COPIA_FINAL_v2 (1) (revisado).pdf"` complica el rastreo de citas.

**Cómo arreglarlo:** un nombre por documento, versionado por sufijo:
`Reglamento_Practicum_2024-04.pdf`, `Reglamento_Practicum_2024-08.pdf`.

---

## 5. Ámbito del documento (dónde subirlo en el sistema)

Al subir un PDF, el rol elige el ámbito:

| Ámbito | Alcance de la búsqueda | Subido por |
|---|---|---|
| `<carrera>|global` | Todo el chat de la carrera | Coordinación |
| `<carrera>|curso:<curso>` | Solo el chat de ese curso | Docente |

**Regla:** normativas y reglamentos → *global*. Sílabos, guías de curso,
cronogramas de un curso concreto → *curso*.

Un documento subido a un curso **no** se filtra al chat general de la
carrera. Un documento subido a nivel global **sí** aparece cuando alguien
pregunta desde un curso (contexto amplio).

---

## 6. Plantilla mínima de un reglamento

```
REGLAMENTO DE [TEMA]
[Nombre completo de la autoridad emisora]
Vigente desde: [fecha]

TÍTULO I – DISPOSICIONES GENERALES

Artículo 1. Objeto
El presente reglamento tiene por objeto...

Artículo 2. Ámbito de aplicación
Este reglamento se aplica a...

TÍTULO II – DEFINICIONES

Artículo 3. Definiciones
Para efectos de este reglamento se entiende por:
a) Practicante: el estudiante que...
b) Tutor académico: el docente que...

TÍTULO III – REQUISITOS Y PROCESO

Artículo 4. Requisitos de inscripción
Para inscribirse el estudiante debe:
a) Haber aprobado...
b) No mantener obligaciones...

Artículo 5. Duración y horas
Las prácticas preprofesionales tienen una duración total de X horas,
distribuidas en:
- Prácticum 1: N horas...
- Prácticum 2: N horas...

[etc.]

DISPOSICIONES FINALES
Este reglamento entra en vigencia a partir de...
```

Cada `Artículo N.` en una línea propia + un título breve. Esto es lo que
la segmentación semántica del indexador (`nucleo/ingest.py`) reconoce
mejor.

---

## 7. Checklist antes de subir un documento

Marca cada punto antes de pulsar "Subir":

- [ ] Es un `.pdf` (no `.docx`, no `.pptx`).
- [ ] Puedes seleccionar texto con el mouse (no es imagen escaneada).
- [ ] Está en español.
- [ ] Pesa menos de 20 MB.
- [ ] El nombre no tiene espacios ni acentos (`Reglamento_Practicum_2026.pdf`).
- [ ] Tiene portada con título y fecha.
- [ ] Las secciones están claramente separadas (Artículo N, Título N, o
      encabezados numerados).
- [ ] Las cifras (horas, plazos, notas) van con su concepto en la misma
      frase.
- [ ] Si contiene diagramas o capturas, están acompañados por texto
      descriptivo.
- [ ] Corriste `python revisar_pdf.py <ruta>` y el resultado fue APTO.

---

## 8. Contacto y proceso de subida

- **Coordinación** sube los reglamentos generales de la carrera desde
  la pestaña *"Reglamentos"* (login como `coord`).
- **Docente** sube documentos de sus cursos desde la pestaña *"Mis
  cursos"* (login como `docente`), después de crear el curso.

Cada documento se indexa **en segundos** al subirlo. Aparece
inmediatamente en las respuestas del chat.

Para eliminar un documento, usa el botón *"Quitar"*. Esto borra el
archivo del disco Y sus fragmentos del índice vectorial, de una sola vez.
