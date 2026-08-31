# -*- coding: utf-8 -*-
"""
ADAPTADOR de embeddings.

Un "embedding" es un vector de numeros que representa el SIGNIFICADO de un texto.
Textos parecidos -> vectores cercanos. Asi es como el sistema encuentra fragmentos
relevantes para una pregunta.

Modelo elegido: paraphrase-multilingual-MiniLM-L12-v2
  - multilingue (funciona en espanol)
  - ligero y rapido (comparado con e5, misma precision con menos peso)
  - la salida es un vector de 384 numeros por texto
"""
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_modelo = None  # se carga una sola vez (tarda ~2s la primera)


def modelo():
    """Carga el modelo la primera vez que se usa (lazy)."""
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(MODEL_NAME)
    return _modelo


def embed(textos):
    """Convierte una lista de textos en una lista de vectores."""
    return modelo().encode(textos, normalize_embeddings=True)
