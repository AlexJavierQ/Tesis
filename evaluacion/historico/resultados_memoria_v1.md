# Medición: costo de la memoria conversacional (v1, primer prompt de reescritura)

> Primera corrida (2 repeticiones). Reveló que el prompt de reescritura dejaba sin completar
> preguntas que empiezan con "¿Y…?", convertía comentarios en preguntas y agregaba detalles
> no pedidos. Se ajustó el prompt (reglas explícitas + ejemplos de otro tema) y se volvió a
> medir: ver `resultados_memoria.md`.

Modelo: `openai/gpt-oss-20b` (Groq). Respuesta en modo `ambos` (curso Practicum 2). Ventana de memoria: 6 mensajes.
Turnos medidos: 56 (2 conversaciones × 7 turnos × 2 repeticiones × 2 estrategias).
El tiempo excluye las esperas por límite de peticiones de Groq (se reportan aparte).

## Promedio por turno

| Estrategia | Llamadas al modelo | Tokens entrada | Tokens salida | Tokens totales | Tiempo (s) | Aciertos |
|---|---|---|---|---|---|---|
| concatenacion | 1.00 | 1222 | 609 | 1831 | 1.73 | 19/26 (73 %) |
| resumen | 2.29 | 1729 | 599 | 2329 | 2.38 | 23/26 (88 %) |

**Diferencia:** la estrategia con resumen usa 1.27× los tokens (+498 por turno) y 1.37× el tiempo (+0.65 s por turno).

Tiempo por turno, concatenacion: mediana 1.44 s (máx. 7.99 s); resumen: mediana 2.53 s (máx. 4.51 s). La mediana es más representativa: hay picos aislados de latencia de Groq.

## Desglose de la estrategia con resumen (promedio por llamada)

| Propósito | Llamadas | Tokens entrada | Tokens salida | Tiempo (s) |
|---|---|---|---|---|
| reescritura | 24 | 491 | 58 | 0.71 |
| resumen | 12 | 353 | 128 | 0.87 |
| respuesta | 28 | 1157 | 495 | 1.34 |

## Cómo se interpretó cada pregunta (repetición 1)

### Horas y entrega del informe

| # | Pregunta | Concatenación | ✓ | Resumen + reescritura | ✓ |
|---|---|---|---|---|---|
| 1 | ¿Cuántas horas de prácticas necesito en total? | ¿Cuántas horas de prácticas necesito en total? | sí | ¿Cuántas horas de prácticas necesito en total? | sí |
| 2 | ¿Y cuántas corresponden al Prácticum 2? | ¿Cuántas horas de prácticas necesito en total? ¿Y cuántas corresponden al Prácticum 2? | sí | ¿Y cuántas corresponden al Prácticum 2? | no |
| 3 | Ya llevo 60 horas en una empresa de software. | Ya llevo 60 horas en una empresa de software. | — | ¿Cuántas horas de prácticas necesito en total si ya he completado 60 horas en una empresa de software? | — |
| 4 | ¿Cuál es el plazo para entregar el informe cuando termine? | ¿Cuál es el plazo para entregar el informe cuando termine? | sí | ¿Cuál es el plazo para entregar el informe cuando termine? | sí |
| 5 | ¿Qué formato uso para eso? | ¿Cuál es el plazo para entregar el informe cuando termine? ¿Qué formato uso para eso? | sí | ¿Qué formato uso para el informe final? | sí |
| 6 | ¿Y quién lo evalúa? | ¿Qué formato uso para eso? ¿Y quién lo evalúa? | no | ¿Y quién evalúa el informe final? | sí |
| 7 | ¿Qué nota necesito para aprobar? | ¿Qué nota necesito para aprobar? | sí | ¿Qué nota necesito obtener en el informe final de Practicum 2 para aprobar el programa? | sí |

### Actores de la práctica (referencia lejana)

| # | Pregunta | Concatenación | ✓ | Resumen + reescritura | ✓ |
|---|---|---|---|---|---|
| 1 | ¿Qué es un practicante preprofesional? | ¿Qué es un practicante preprofesional? | sí | ¿Qué es un practicante preprofesional? | sí |
| 2 | ¿Y en qué se diferencia de un pasante? | ¿Qué es un practicante preprofesional? ¿Y en qué se diferencia de un pasante? | no | ¿Y en qué se diferencia de un pasante? | no |
| 3 | ¿Cuáles son las funciones del tutor externo? | ¿Cuáles son las funciones del tutor externo? | sí | ¿Cuáles son las funciones del tutor externo? | sí |
| 4 | ¿Y las del tutor académico? | ¿Cuáles son las funciones del tutor externo? ¿Y las del tutor académico? | no | ¿Cuáles son las funciones del tutor académico? | sí |
| 5 | Volviendo a lo primero, ¿esa figura recibe algún pago? | ¿Y las del tutor académico? Volviendo a lo primero, ¿esa figura recibe algún pago? | no | Volviendo a lo primero, ¿el practicante preprofesional recibe algún pago? | sí |
| 6 | ¿Hasta cuándo puedo postular a una plaza? | ¿Hasta cuándo puedo postular a una plaza? | sí | ¿Hasta cuándo puedo postular a una plaza? | sí |
| 7 | ¿Y quién tiene que validar esa postulación? | ¿Hasta cuándo puedo postular a una plaza? ¿Y quién tiene que validar esa postulación? | sí | ¿Quién debe validar la postulación? | sí |

Llamadas fallidas al modelo: 0. Tiempo total esperando por límite de peticiones (excluido): 0.0 s.

*Aciertos*: la respuesta contiene el dato esperado (palabra clave). Es una medida aproximada; no reemplaza la evaluación con RAGAS.