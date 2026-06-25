# Resultados de validación de herramientas

Pruebas para verificar que las herramientas elegidas son las correctas.
Reproducible: `python pruebas_herramientas.py` (se puede correr en vivo).

> Nota: el set de evaluación son 6 preguntas sobre el reglamento de demo (corto),
> así que los porcentajes son indicativos. Con los reglamentos reales conviene
> volver a correrlo para confirmar; la metodología es la misma.

## 1. Lector de PDF — PyMuPDF vs pypdf
| Herramienta | Texto extraído | Tiempo |
|---|---|---|
| **PyMuPDF** | 1399 caracteres | **91 ms** |
| pypdf | 1398 caracteres | 214 ms |

**Conclusión:** mismo texto, pero PyMuPDF es **~2.3× más rápido**. Se confirma PyMuPDF.

## 2. Tamaño de chunk (modelo MiniLM)
| chunk | Fragmentos | Precisión top-1 |
|---|---|---|
| 300 | 7 | 83.3 % |
| **500** | 4 | **100 %** |
| 800 | 2 | 66.7 % |

**Conclusión:** 500 es el punto óptimo. Muy chico fragmenta de más; muy grande
mezcla temas y pierde precisión. Se confirma `chunk_size = 500`.

## 3. Embeddings — MiniLM vs multilingual-e5
| Modelo | Precisión top-1 | Tiempo/consulta |
|---|---|---|
| **paraphrase-multilingual-MiniLM-L12** | 100 % | 19.5 ms |
| multilingual-e5-small | 100 % | 20.6 ms |

**Conclusión:** misma precisión en español, y MiniLM es más liviano y rápido.
No hace falta el modelo más pesado. Se confirma MiniLM (se puede re-evaluar con
los reglamentos reales si se quiere exprimir más calidad).

## 4. Latencia de recuperación
- **16.6 ms por consulta** (solo la búsqueda; el LLM suma ~1–2 s).
- Muy por debajo del requisito de **respuesta < 8 s**. Se cumple con holgura.

## Por qué estas pruebas son fáciles de hacer (arquitectura modular)
Cada herramienta está aislada en un adaptador (`embeddings.py`, `vectorstore.py`,
`llm.py`, `pdfreader.py`). Comparar una alternativa = cambiar una línea o un
archivo, sin tocar el resto del sistema. Eso es lo que permite validar y, si hace
falta, **cambiar de herramienta sin romper nada**.
