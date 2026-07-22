# Evaluación del sistema sobre el corpus real

Preguntas evaluadas: **85** (57 dentro del corpus, 28 fuera).

## Recuperación

| Métrica | Valor |
|---|---|
| recall@8 | 93.0 % |
| precision@1 | 47.4 % |
| MRR | 0.635 |
| Latencia de recuperación (mediana) | 16.8 ms |
| Latencia total (mediana) | 0.48 s |
| Latencia total (máxima) | 1.45 s |
| Cumple RNF3 (< 8 s) | sí |

## Comportamiento de respuesta

| Métrica | Valor |
|---|---|
| Responde con respaldo (dentro del corpus) | 93.0 % |
| Se abstiene correctamente (fuera del corpus) | 39.3 % |

### Abstención por cercanía al dominio

Cuanto más se parece la pregunta al dominio, más difícil es distinguirla por similitud.

| Cercanía | n | Se abstiene | Distancia mín. (mediana) |
|---|---|---|---|
| lejana | 8 | 100 % | 0.777 |
| media | 10 | 30 % | 0.613 |
| cercana | 10 | 0 % | 0.495 |

## Detalle por pregunta

| # | Pregunta | Esperado | Pos. | dist. mín. | Respaldo | Correcto |
|---|---|---|---|---|---|---|
| 1 | cuantas horas de practicas necesito en total | responder | 1 | 0.200 | si | OK |
| 2 | cual es el total de horas del practicum | responder | 1 | 0.236 | si | OK |
| 3 | cuantas horas debo completar para terminar las practicas | responder | 1 | 0.255 | si | OK |
| 4 | cuantas horas son en practicum 1 | responder | 1 | 0.273 | si | OK |
| 5 | cuantas horas puedo dedicar por semana | responder | 1 | 0.411 | si | OK |
| 6 | cuantas horas al dia puedo hacer si tengo clases | responder | 2 | 0.326 | si | OK |
| 7 | que necesito aprobar antes de empezar practicum 1 | responder | 1 | 0.377 | si | OK |
| 8 | desde que semestre puedo hacer practicas | responder | 2 | 0.375 | si | OK |
| 9 | cual es el prerrequisito de practicum 2 | responder | 1 | 0.360 | si | OK |
| 10 | puedo hacer practicum 1 y practicum 2 al mismo tiempo | responder | 3 | 0.547 | si | OK |
| 11 | me puedo convalidar horas de practicas por mi trabajo actu | responder | 1 | 0.291 | si | OK |
| 12 | que porcentaje de horas puedo convalidar si ya trabajo | responder | 1 | 0.320 | si | OK |
| 13 | que documentos necesito para pedir convalidacion | responder | 2 | 0.444 | si | OK |
| 14 | donde puedo hacer las practicas | responder | 1 | 0.417 | si | OK |
| 15 | puedo hacer las practicas preprofesionales en el extranjer | responder | 1 | 0.366 | si | OK |
| 16 | con cuanta anticipacion pido practicas en el exterior | responder | 1 | 0.358 | si | OK |
| 17 | puedo cambiar de empresa a mitad del practicum | responder | 7 | 0.424 | si | OK |
| 18 | pierdo las horas si cambio de organizacion | responder | 2 | 0.310 | si | OK |
| 19 | que pasa si la empresa incumple el convenio de practicas | responder | 1 | 0.400 | si | OK |
| 20 | me pagan un sueldo durante las practicas preprofesionales | responder | 1 | 0.385 | si | OK |
| 21 | la empresa puede darme dinero para transporte | responder | 1 | 0.738 | no | **FALLA** |
| 22 | tengo seguro estudiantil mientras hago las practicas | responder | 1 | 0.300 | si | OK |
| 23 | el seguro me cubre si hago practicas fuera del pais | responder | 2 | 0.367 | si | OK |
| 24 | cuantas faltas puedo tener en las practicas | responder | 6 | 0.485 | si | OK |
| 25 | cada cuanto me reuno con mi tutor | responder | 2 | 0.344 | si | OK |
| 26 | quien evalua mi informe | responder | 3 | 0.591 | no | **FALLA** |
| 27 | que hago si mi tutor no responde mis correos | responder | 2 | 0.437 | si | OK |
| 28 | que formato uso para el informe final | responder | 1 | 0.380 | si | OK |
| 29 | que formato se usa para el plan de practicas | responder | 1 | 0.386 | si | OK |
| 30 | donde consigo los formatos oficiales | responder | 1 | 0.425 | si | OK |
| 31 | en cuanto tiempo debo entregar el informe final | responder | 2 | 0.303 | si | OK |
| 32 | cual es el plazo de entrega del informe | responder | 2 | 0.326 | si | OK |
| 33 | por donde entrego el informe | responder | 4 | 0.556 | no | **FALLA** |
| 34 | puedo pedir prorroga para entregar el informe de practicas | responder | 1 | 0.410 | si | OK |
| 35 | cuantos dias extra me dan de prorroga | responder | 4 | 0.481 | si | OK |
| 36 | cual es la nota minima para aprobar el practicum | responder | 2 | 0.371 | si | OK |
| 37 | con cuanto apruebo las practicas | responder | — | 0.413 | si | OK |
| 38 | que pasa si repruebo el practicum | responder | 5 | 0.527 | si | OK |
| 39 | a quien consulto si el reglamento no resuelve mi duda | responder | 5 | 0.511 | si | OK |
| 40 | que titulo otorga la carrera de computacion | responder | 1 | 0.354 | si | OK |
| 41 | cuanto dura la carrera | responder | 1 | 0.560 | si | OK |
| 42 | cual es la asistencia minima exigida | responder | 4 | 0.366 | si | OK |
| 43 | cuantas matriculas tengo por asignatura | responder | 1 | 0.376 | si | OK |
| 44 | quien autoriza la tercera matricula | responder | 1 | 0.478 | si | OK |
| 45 | que necesito para graduarme | responder | 1 | 0.496 | si | OK |
| 46 | que es el trabajo de integracion curricular | responder | 2 | 0.355 | si | OK |
| 47 | como solicito un certificado de matricula | responder | 1 | 0.417 | si | OK |
| 48 | cuanto tardan en emitir un certificado | responder | 1 | 0.307 | si | OK |
| 49 | en que consiste practicum 1 | responder | — | 0.474 | si | OK |
| 50 | como se evalua practicum 1 | responder | 6 | 0.464 | si | OK |
| 51 | cuanto vale el informe parcial en practicum 1 | responder | 2 | 0.446 | no | **FALLA** |
| 52 | que entregables tiene practicum 1 | responder | 7 | 0.575 | si | OK |
| 53 | que aprendo en practicum 1 | responder | 3 | 0.400 | si | OK |
| 54 | en que consiste practicum 2 | responder | 6 | 0.503 | si | OK |
| 55 | cuanto pesa el proyecto aplicado en practicum 2 | responder | 4 | 0.480 | si | OK |
| 56 | que entrego en practicum 2 | responder | — | 0.493 | si | OK |
| 57 | tengo que presentar el proyecto en practicum 2 | responder | — | 0.437 | si | OK |
| 58 | puedo hacer las practicas en modalidad remota desde casa | abstenerse | — | 0.568 | si | **FALLA** |
| 59 | las horas de voluntariado cuentan para el practicum | abstenerse | — | 0.274 | si | **FALLA** |
| 60 | puedo hacer practicas en dos empresas a la vez | abstenerse | — | 0.510 | si | **FALLA** |
| 61 | que pasa si me enfermo durante las practicas | abstenerse | — | 0.539 | si | **FALLA** |
| 62 | la nota del practicum cuenta para mi promedio de graduacio | abstenerse | — | 0.433 | si | **FALLA** |
| 63 | hay cupo limitado de plazas por empresa | abstenerse | — | 0.498 | si | **FALLA** |
| 64 | el tutor empresarial tiene que ser ingeniero titulado | abstenerse | — | 0.432 | si | **FALLA** |
| 65 | puedo empezar las practicas durante las vacaciones | abstenerse | — | 0.491 | si | **FALLA** |
| 66 | quien firma mi certificado de horas de practicas | abstenerse | — | 0.332 | si | **FALLA** |
| 67 | puedo hacer las practicas en una empresa de un familiar | abstenerse | — | 0.551 | si | **FALLA** |
| 68 | cual es el horario de atencion de la biblioteca | abstenerse | — | 0.468 | si | **FALLA** |
| 69 | cuanto cuesta la matricula del proximo ciclo | abstenerse | — | 0.617 | no | OK |
| 70 | que beca puedo solicitar para transporte | abstenerse | — | 0.633 | si | **FALLA** |
| 71 | cuando son las elecciones estudiantiles | abstenerse | — | 0.577 | si | **FALLA** |
| 72 | donde queda el departamento de bienestar estudiantil | abstenerse | — | 0.489 | si | **FALLA** |
| 73 | como me inscribo en los equipos deportivos de la universid | abstenerse | — | 0.647 | no | OK |
| 74 | hay convenios de intercambio con universidades de espana | abstenerse | — | 0.609 | si | **FALLA** |
| 75 | cual es el correo del rector | abstenerse | — | 0.589 | si | **FALLA** |
| 76 | cuando empiezan las vacaciones del ciclo | abstenerse | — | 0.634 | si | **FALLA** |
| 77 | donde puedo almorzar dentro del campus | abstenerse | — | 0.784 | no | OK |
| 78 | quien gano el mundial de futbol de 2022 | abstenerse | — | 0.686 | no | OK |
| 79 | como preparo un ceviche de camaron | abstenerse | — | 0.768 | no | OK |
| 80 | cual es la capital de australia | abstenerse | — | 0.848 | no | OK |
| 81 | cuanto cuesta un pasaje de avion a madrid | abstenerse | — | 0.785 | no | OK |
| 82 | que pelicula gano el oscar este ano | abstenerse | — | 0.744 | no | OK |
| 83 | como cambio el aceite de mi carro | abstenerse | — | 0.853 | no | OK |
| 84 | cual es el pronostico del clima para manana | abstenerse | — | 0.677 | no | OK |
| 85 | escribeme un poema sobre el mar | abstenerse | — | 0.809 | no | OK |

## Fallos a revisar (25)

- **la empresa puede darme dinero para transporte** — no respondió teniendo el fragmento (distancia mínima 0.738)
- **quien evalua mi informe** — no respondió teniendo el fragmento (distancia mínima 0.591)
- **por donde entrego el informe** — no respondió teniendo el fragmento (distancia mínima 0.556)
- **con cuanto apruebo las practicas** — no recuperó el fragmento correcto (distancia mínima 0.413)
- **en que consiste practicum 1** — no recuperó el fragmento correcto (distancia mínima 0.474)
- **cuanto vale el informe parcial en practicum 1** — no respondió teniendo el fragmento (distancia mínima 0.446)
- **que entrego en practicum 2** — no recuperó el fragmento correcto (distancia mínima 0.493)
- **tengo que presentar el proyecto en practicum 2** — no recuperó el fragmento correcto (distancia mínima 0.437)
- **puedo hacer las practicas en modalidad remota desde casa** — debía abstenerse y respondió (distancia mínima 0.568)
- **las horas de voluntariado cuentan para el practicum** — debía abstenerse y respondió (distancia mínima 0.274)
- **puedo hacer practicas en dos empresas a la vez** — debía abstenerse y respondió (distancia mínima 0.510)
- **que pasa si me enfermo durante las practicas** — debía abstenerse y respondió (distancia mínima 0.539)
- **la nota del practicum cuenta para mi promedio de graduacion** — debía abstenerse y respondió (distancia mínima 0.433)
- **hay cupo limitado de plazas por empresa** — debía abstenerse y respondió (distancia mínima 0.498)
- **el tutor empresarial tiene que ser ingeniero titulado** — debía abstenerse y respondió (distancia mínima 0.432)
- **puedo empezar las practicas durante las vacaciones** — debía abstenerse y respondió (distancia mínima 0.491)
- **quien firma mi certificado de horas de practicas** — debía abstenerse y respondió (distancia mínima 0.332)
- **puedo hacer las practicas en una empresa de un familiar** — debía abstenerse y respondió (distancia mínima 0.551)
- **cual es el horario de atencion de la biblioteca** — debía abstenerse y respondió (distancia mínima 0.468)
- **que beca puedo solicitar para transporte** — debía abstenerse y respondió (distancia mínima 0.633)
- **cuando son las elecciones estudiantiles** — debía abstenerse y respondió (distancia mínima 0.577)
- **donde queda el departamento de bienestar estudiantil** — debía abstenerse y respondió (distancia mínima 0.489)
- **hay convenios de intercambio con universidades de espana** — debía abstenerse y respondió (distancia mínima 0.609)
- **cual es el correo del rector** — debía abstenerse y respondió (distancia mínima 0.589)
- **cuando empiezan las vacaciones del ciclo** — debía abstenerse y respondió (distancia mínima 0.634)

---

Parámetros: top-k = 8, umbral de distancia = 0.65, modelo = `llama-3.1-8b-instant` (groq).

Reproducible con `python evaluacion.py`.
