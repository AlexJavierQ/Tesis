# Evaluación de LLMs por cuota gratuita (sin perder calidad)

Motivo: Gemini Flash-Lite con la key de prueba (`AQ.`) daba solo **20 req/día**.
Se evaluaron alternativas con mejor cuota gratuita.

## Primer hallazgo: era la key, no Gemini
Un Gemini 2.5 Flash-Lite con **key real de Google AI Studio (`AIzaSy...`)** tiene
**~1,000–1,500 req/día**, no 20. La key `AQ.` no es del tipo estándar.
→ Arreglo inmediato: sacar una key nueva en https://aistudio.google.com/

## Comparativa (free tier, junio 2026)
| Proveedor / modelo | Cuota gratis | RPM | Calidad | Privacidad |
|---|---|---|---|---|
| **Groq · Llama 3.1 8B** | **14,400 req/día** | 30 | Buena para RAG | OK |
| Groq · Llama 3.3 70B | 1,000 req/día | 30 | Muy buena | OK |
| Cerebras · Llama 3.3 70B | ~1M tokens/día | — | Muy buena | OK |
| Gemini 2.5 Flash-Lite (key real) | ~1,000–1,500 req/día | 15–30 | Buena | OK |
| OpenRouter (modelos free) | 50 req/día (1,000 si pagas $10) | 20 | Variable | OK |
| Mistral (Experiment) | ~1B tokens/mes | — | Buena | ❌ exige ceder datos para entrenamiento |
| Ollama (local) | ilimitado | — | Según modelo | ✅ máxima (no sale nada) |

## Recomendación para el TIC
1. **Inmediato:** sacar key real de AI Studio (`AIza...`) → debería subir a ~1,000–1,500/día.
2. **Más cuota:** **Groq con Llama 3.1 8B = 14,400/día**, rápido y sin tarjeta. Ya está
   integrado como opción intercambiable.
3. **Calidad para RAG:** la tarea es responder a partir del contexto entregado (no razonar
   de cero), así que Llama 8B y Gemini Flash-Lite rinden bien; no hace falta un modelo caro.
4. **Privacidad (importante para datos institucionales):** evitar Mistral free (entrena con
   tus datos). Para máxima privacidad en producción → **Ollama local** (Llama/Qwen): sin
   cuota, sin costo, y los documentos no salen de la UTPL. Buen punto para la tesis.

## Cómo cambiar de proveedor (gracias a la arquitectura modular)
Solo variables de entorno, sin tocar el código:

```bash
# Opción A — Gemini (por defecto)
set GEMINI_API_KEY=AIza...        # key real de AI Studio
streamlit run app.py

# Opción B — Groq (14.400 req/día)
#   1) crea tu key gratis en https://console.groq.com  (sin tarjeta)
set LLM_PROVIDER=groq
set GROQ_API_KEY=gsk_...
streamlit run app.py
```

Para subir calidad en Groq, cambia `GROQ_MODEL` en `llm.py` a `llama-3.3-70b-versatile`
(1,000 req/día). Todo el resto del sistema queda igual: eso es lo que permite el adaptador.
