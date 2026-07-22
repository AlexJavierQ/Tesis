# Estrategia anti-alucinación: qué se probó y qué funcionó

Registro experimental de las alternativas evaluadas para evitar que el asistente
responda cuando el corpus no contiene la respuesta.

Todas las mediciones usan el mismo banco (`preguntas_eval.json`, 85 preguntas:
57 dentro del corpus y 28 fuera) y son reproducibles con `python evaluacion.py`.

> **Alcance:** el corpus es ficticio (ver `make_demo_pdf.py`). Estas cifras sirven
> para comparar alternativas entre sí, no para afirmar el rendimiento del sistema
> sobre normativa real.

## El problema

Las preguntas fuera del corpus no son todas iguales. Se clasificaron en tres
bandas según su parecido al dominio:

| Banda | Ejemplo | Distancia mediana |
|---|---|---|
| lejana | "¿quién ganó el mundial de 2022?" | 0.777 |
| media | "¿cuál es el horario de la biblioteca?" | 0.613 |
| cercana | "¿las horas de voluntariado cuentan?" | 0.495 |

La banda cercana comparte casi todo el vocabulario con los documentos. Solo
cambia el hecho consultado, y eso es invisible para la similitud vectorial.

Caso límite medido: *"¿me puedo convalidar horas por mi trabajo actual?"* tiene
distancia **0.211**, más cercana que la mayoría de preguntas legítimas. Ningún
umbral la separa sin rechazar también las preguntas reales.

## Alternativas evaluadas

### 1. Calibrar el umbral de similitud (capa 1)

Barrido completo sobre el banco:

| Umbral | Acierta dentro | Acierta fuera |
|---|---|---|
| 0.48 | 67 % | 100 % |
| 0.60 | 93 % | 67 % |
| 0.65 (actual) | 96 % | 33 % |
| 0.70 | 100 % | 33 % |

**Resultado:** las distribuciones se solapan (0.499–0.692). No existe un umbral
que separe ambas clases. Bajarlo a 0.48 da abstención perfecta pero rechaza un
tercio de las preguntas legítimas, lo que destruye la utilidad del asistente.

**Decisión:** se mantiene 0.65 como compromiso, documentando el límite.

### 2. Reforzar el prompt del generador (capa 2)

Se reescribió el prompt para exigir explícitamente que el dato concreto aparezca
en el contexto, con la instrucción *"que un fragmento trate el tema NO significa
que contenga la respuesta"*.

| | Abstención global | Banda cercana |
|---|---|---|
| Prompt original | 46.4 % | 10 % |
| Prompt reforzado | 42.9 % | 10 % |

**Resultado: no mejora.** Dentro del margen de ruido, incluso ligeramente peor.
La instrucción no cambia el juicio del modelo sobre qué cuenta como respaldo.

### 3. Segunda llamada de verificación (capa 3)

Se añadió un verificador independiente: una segunda llamada al modelo, con
temperatura 0, que recibe contexto + pregunta + respuesta y emite un veredicto
binario (RESPALDADA / INFUNDADA) sin tarea de redacción.

| | Abstención global | Banda cercana | Latencia mediana |
|---|---|---|---|
| Sin verificación | 42.9 % | 10 % | 0.48 s |
| Con verificación | 42.9 % | 10 % | 0.48 s (máx. 2.76 s) |

Medición directa del aporte sobre las 10 preguntas de la banda cercana:

```
el generador se abstuvo solo : 3
el VERIFICADOR las rechazo   : 0   <-- aporte real de la 2a llamada
pasaron (alucinacion)        : 1
```

**Resultado: aporte nulo.** El verificador no rechazó ninguna respuesta
infundada. La causa es que **es el mismo modelo y comparte su punto ciego**: si
el generador concluyó que el contexto responde la pregunta, el verificador
concluye lo mismo al leer lo mismo. La auto-verificación detecta descuidos, no
errores sistemáticos de criterio.

Ejemplo representativo:

> **Pregunta:** ¿puedo hacer prácticas en dos empresas a la vez?
> **Respuesta:** "No. Practicum 1 y Practicum 2 se cursan en periodos académicos distintos."
> **Veredicto del verificador:** RESPALDADA

El modelo confundió "dos empresas" con "dos niveles"; el verificador vio en el
contexto la frase "no se permite cursar ambos" y dio la respuesta por buena.

**Decisión:** implementado pero **apagado por defecto** (`VERIFICAR_RESPUESTA=1`
lo enciende). No se justifica el coste de una llamada extra por consulta para un
beneficio medido de cero.

### 4. Cita literal verificada mecánicamente (capa 3, determinista)

Se obliga al generador a devolver, junto a la respuesta, la frase textual del
contexto que la respalda (`FUNDAMENTO`). Esa frase se compara contra el contexto
por coincidencia de subcadena más larga (normalizada, umbral 0.72): si el modelo
no puede aportar una frase real que sostenga su respuesta, se abstiene. La
verificación es determinista y **no vuelve a preguntar al modelo**, así que no
comparte su punto ciego y no añade latencia.

Como el sistema es no determinista (generación a temperatura 0.2), se mide sobre
5 corridas y se reporta media ± desviación:

| | Abstención fuera del corpus | Responde dentro del corpus |
|---|---|---|
| Sin cita literal | 43.6 % ± 3.5 | 95.9 % |
| Con cita literal | 40.0 % ± 1.4 | 93.0 % |

**Resultado: no mejora la abstención** (la diferencia queda dentro del ruido) y
cuesta ~3 puntos de respuestas legítimas.

La razón vuelve a ser la naturaleza de los fallos. En la banda cercana el modelo
no *fabrica* un dato: *malinterpreta* una frase real y adyacente. Ejemplo:

> **Pregunta:** ¿puedo hacer prácticas en dos empresas a la vez?
> **Respuesta:** "No, Practicum 1 y 2 se cursan en periodos distintos."
> **Fundamento citado:** "no se permite cursar ambos niveles en el mismo periodo"

El fundamento **existe de verdad** en el contexto, así que la verificación por
cadena lo aprueba. El error no está en la cita, está en el salto de la cita a la
respuesta. La verificación textual atrapa la *fabricación*, no el *razonamiento
defectuoso*, y los fallos de este corpus son del segundo tipo.

**Lo que sí garantiza:** que toda respuesta mostrada se apoya en una frase real
del corpus. Elimina por completo la fabricación pura (números o hechos inventados
que no están en ningún documento), que es el modo de fallo más grave aunque sea
raro en este banco. Coste: cero latencia, ~3 pp de respuestas legítimas menos.

**Decisión:** se deja **encendida por defecto** (`CITA_LITERAL=0` la apaga). No
por la abstención —que no mejora— sino por la garantía de fundamentación: para un
sistema cuya tesis es "cero alucinaciones", que ninguna respuesta pueda apoyarse
en texto inexistente es una propiedad estructural que vale el coste, y es gratis
en tiempo.

### 5. Mejorar la segmentación del corpus (indirecto)

No apuntaba a la alucinación, pero fue lo único que movió la aguja.

El troceado original cortaba cada 500 caracteres con 80 de solape, generando
fragmentos vecinos casi idénticos que ocupaban todo el top-k. Además indexaba
los avisos repetidos en la cabecera de cada documento, que competían en toda
consulta.

Se sustituyó por segmentación **por unidad normativa** (artículo, título,
párrafo), sin partir un artículo, y se eliminan los avisos antes de indexar.

| | Fragmentos | recall | MRR | Abstención |
|---|---|---|---|---|
| Troceado por caracteres | 225 | 82.5 % | 0.628 | 39.3 % |
| Segmentación semántica | 56 | 93.0 % (k=8) | 0.635 | 42.9 % |

También resolvió el incumplimiento del RNF3: la latencia máxima bajó de 8.06 s
a 0.88 s, porque dejó de enviarse contexto redundante al modelo.

## Conclusión

De las cinco vías, **solo la segmentación del corpus mejoró la abstención de
forma medible**. Las tres intervenciones dirigidas a la alucinación —prompt
reforzado, auto-verificación por LLM y cita literal— no movieron la abstención
más allá del ruido.

El hallazgo de fondo es *por qué*: los fallos residuales no son fabricaciones,
son **errores de razonamiento sobre frases reales y adyacentes**. El modelo no
inventa; malinterpreta un artículo del mismo tema. Ninguna capa que pregunte al
mismo modelo, ni la verificación de que la cita existe, corrige eso, porque el
error no está en el dato citado sino en la inferencia. Esa es la frontera real
del enfoque RAG con un solo modelo.

La cita literal se conserva encendida no por la abstención, sino porque garantiza
—de forma determinista y sin coste de latencia— que ninguna respuesta se apoye en
texto inexistente. Es la única defensa estructural contra la fabricación pura.

Cifras finales del sistema (cita literal activa, media de 5 corridas): abstiene
el **100 %** de las preguntas ajenas al dominio, el **~35 %** de las
universitarias generales y el **~10 %** de las preguntas sobre prácticum no
cubiertas por el corpus. Esa última banda es el límite documentado.

## Líneas no exploradas

Dos vías que sí podrían atacar el error de razonamiento, porque no dependen del
juicio del modelo generador:

1. **Modelo verificador distinto** al generador (otro proveedor o familia), para
   romper la correlación de errores de razonamiento. Coste: una llamada extra a
   otro modelo.
2. **Modelo de inferencia textual (NLI)** local tipo cross-encoder, entrenado
   para decidir vinculación premisa→hipótesis. Sesgo inductivo distinto al de un
   LLM generativo y sin dependencia de un servicio externo.

Ambas quedan como trabajo futuro. Requieren un segundo modelo, lo que excede el
alcance de un MVP de coste cero, pero son el camino natural si se quiere cerrar
la banda cercana.
