# Medición: costo de la memoria conversacional (v2, prompt de reescritura ajustado)

> Se usa solo la **repetición 1** (completa en ambas estrategias, 0 fallos). La repetición 2
> agotó la cuota DIARIA gratuita de Groq (200.000 tokens/día) a mitad de la estrategia con
> resumen; esos turnos fallaron y se excluyen. Los datos crudos de todo están en el .json.

Modelo: `openai/gpt-oss-20b` (Groq). Respuesta en modo `ambos` (curso Practicum 2). Ventana de memoria: 6 mensajes.
Turnos medidos: 28 (2 conversaciones × 7 turnos × 1 repeticiones × 2 estrategias).
El tiempo excluye las esperas por límite de peticiones de Groq (se reportan aparte).

## Promedio por turno

| Estrategia | Llamadas al modelo | Tokens entrada | Tokens salida | Tokens totales | Tiempo (s) | Aciertos |
|---|---|---|---|---|---|---|
| concatenacion | 1.00 | 1222 | 681 | 1902 | 1.99 | 10/13 (77 %) |
| resumen | 2.29 | 1894 | 643 | 2537 | 2.95 | 13/13 (100 %) |

**Diferencia:** la estrategia con resumen usa 1.33× los tokens (+635 por turno) y 1.48× el tiempo (+0.96 s por turno).

Tiempo por turno, concatenacion: mediana 1.37 s (máx. 6.97 s); resumen: mediana 2.41 s (máx. 9.63 s). La mediana es más representativa: hay picos aislados de latencia de Groq.

## Desglose de la estrategia con resumen (promedio por llamada)

| Propósito | Llamadas | Tokens entrada | Tokens salida | Tiempo (s) |
|---|---|---|---|---|
| reescritura | 12 | 660 | 58 | 0.81 |
| resumen | 6 | 356 | 215 | 0.82 |
| respuesta | 14 | 1176 | 502 | 1.85 |

## Cómo se interpretó cada pregunta (repetición 1)

### Horas y entrega del informe

| # | Pregunta | Concatenación | ✓ | Resumen + reescritura | ✓ |
|---|---|---|---|---|---|
| 1 | ¿Cuántas horas de prácticas necesito en total? | ¿Cuántas horas de prácticas necesito en total? | sí | ¿Cuántas horas de prácticas necesito en total? | sí |
| 2 | ¿Y cuántas corresponden al Prácticum 2? | ¿Cuántas horas de prácticas necesito en total? ¿Y cuántas corresponden al Prácticum 2? | sí | ¿Cuántas horas corresponden al Prácticum 2? | sí |
| 3 | Ya llevo 60 horas en una empresa de software. | Ya llevo 60 horas en una empresa de software. | — | Ya llevo 60 horas en una empresa de software. | — |
| 4 | ¿Cuál es el plazo para entregar el informe cuando termine? | ¿Cuál es el plazo para entregar el informe cuando termine? | sí | ¿Cuál es el plazo para entregar el informe de Practicum 2 cuando termine? | sí |
| 5 | ¿Qué formato uso para eso? | ¿Cuál es el plazo para entregar el informe cuando termine? ¿Qué formato uso para eso? | sí | ¿Qué formato uso para el informe final? | sí |
| 6 | ¿Y quién lo evalúa? | ¿Qué formato uso para eso? ¿Y quién lo evalúa? | no | ¿Quién evalúa el informe final? | sí |
| 7 | ¿Qué nota necesito para aprobar? | ¿Qué nota necesito para aprobar? | sí | ¿Qué nota necesito para aprobar? | sí |

### Actores de la práctica (referencia lejana)

| # | Pregunta | Concatenación | ✓ | Resumen + reescritura | ✓ |
|---|---|---|---|---|---|
| 1 | ¿Qué es un practicante preprofesional? | ¿Qué es un practicante preprofesional? | sí | ¿Qué es un practicante preprofesional? | sí |
| 2 | ¿Y en qué se diferencia de un pasante? | ¿Qué es un practicante preprofesional? ¿Y en qué se diferencia de un pasante? | no | ¿En qué se diferencia un practicante preprofesional de un pasante? | sí |
| 3 | ¿Cuáles son las funciones del tutor externo? | ¿Cuáles son las funciones del tutor externo? | sí | ¿Cuáles son las funciones del tutor externo? | sí |
| 4 | ¿Y las del tutor académico? | ¿Cuáles son las funciones del tutor externo? ¿Y las del tutor académico? | sí | ¿Cuáles son las funciones del tutor académico? | sí |
| 5 | Volviendo a lo primero, ¿esa figura recibe algún pago? | ¿Y las del tutor académico? Volviendo a lo primero, ¿esa figura recibe algún pago? | no | ¿El practicante preprofesional recibe algún pago? | sí |
| 6 | ¿Hasta cuándo puedo postular a una plaza? | ¿Hasta cuándo puedo postular a una plaza? | sí | ¿Hasta cuándo puedo postular a una plaza? | sí |
| 7 | ¿Y quién tiene que validar esa postulación? | ¿Hasta cuándo puedo postular a una plaza? ¿Y quién tiene que validar esa postulación? | sí | ¿Quién debe validar la postulación? | sí |

Llamadas fallidas al modelo: 0. Tiempo total esperando por límite de peticiones (excluido): 0.0 s.

*Aciertos*: la respuesta contiene el dato esperado (palabra clave). Es una medida aproximada; no reemplaza la evaluación con RAGAS.