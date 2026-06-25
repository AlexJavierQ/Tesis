# -*- coding: utf-8 -*-
"""
ADAPTADOR de embeddings. Aísla el modelo que convierte texto en vectores.
Para cambiar de modelo (ej. MiniLM -> e5) solo cambias MODEL_NAME aquí;
nada más del sistema se entera.
"""
from sentence_transformers import SentenceTransformer

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"   # <- cambiar aquí para probar otro
_model = None


def model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed(texts):
    """texts: list[str] -> matriz de vectores (numpy)."""
    return model().encode(texts, convert_to_numpy=True, normalize_embeddings=True)
