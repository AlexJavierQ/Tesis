# -*- coding: utf-8 -*-
"""
ADAPTADOR de base de datos vectorial (ChromaDB).

Guarda cada fragmento junto con:
  - su vector (embedding)
  - metadatos: archivo de origen, pagina, ambito (scope)
  - un id unico

Y sabe buscar por similitud: dada una pregunta, devuelve los k fragmentos
mas cercanos en significado.
"""
import os
import chromadb
from chromadb.utils import embedding_functions
from nucleo import embeddings

BASE = os.path.dirname(__file__)
CARPETA = os.path.join(os.path.dirname(BASE), "datos", "chroma_db")
COLECCION = "practicum"


def coleccion():
    """Abre (o crea) la coleccion de ChromaDB."""
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=embeddings.MODEL_NAME
    )
    cliente = chromadb.PersistentClient(path=CARPETA)
    return cliente.get_or_create_collection(
        name=COLECCION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},  # metrica de similitud coseno
    )


def agregar(textos, metadatos, ids):
    """Guarda una lista de fragmentos con sus metadatos y ids."""
    coleccion().add(documents=textos, metadatas=metadatos, ids=ids)


def buscar(pregunta, k=8, filtro=None):
    """
    Devuelve los k fragmentos mas parecidos a la pregunta.
    filtro: por ejemplo {"scope": {"$in": ["computacion|global"]}}
    """
    col = coleccion()
    if col.count() == 0:
        return []
    resultado = col.query(
        query_texts=[pregunta],
        n_results=min(k, col.count()),
        where=filtro,
    )
    salida = []
    for texto, meta, distancia in zip(
        resultado["documents"][0],
        resultado["metadatas"][0],
        resultado["distances"][0],
    ):
        salida.append({"texto": texto, "meta": meta, "distancia": distancia})
    return salida


def borrar(filtro):
    """Elimina fragmentos que cumplan el filtro (por ejemplo un documento entero)."""
    coleccion().delete(where=filtro)


def contar():
    """Cuantos fragmentos hay indexados en total."""
    return coleccion().count()
