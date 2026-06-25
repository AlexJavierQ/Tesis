# -*- coding: utf-8 -*-
"""
ADAPTADOR de base vectorial. Aísla ChromaDB.
Para cambiar a otra (Qdrant, FAISS, etc.) solo reimplementas este archivo
manteniendo las mismas funciones (add / query / delete / count / reset).
"""
import os
import chromadb
from chromadb.utils import embedding_functions
import embeddings as emb

BASE = os.path.dirname(__file__)
DB_DIR = os.path.join(BASE, "chroma_db")
COLLECTION = "practicum"
_col = None


def get_collection():
    global _col
    if _col is None:
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=emb.MODEL_NAME)
        client = chromadb.PersistentClient(path=DB_DIR)
        _col = client.get_or_create_collection(
            name=COLLECTION, embedding_function=ef, metadata={"hnsw:space": "cosine"})
    return _col


def add(docs, metas, ids):
    c = get_collection()
    for i in range(0, len(docs), 200):
        c.add(documents=docs[i:i+200], metadatas=metas[i:i+200], ids=ids[i:i+200])


def query(text, k, where=None):
    """Devuelve lista de (documento, metadata, distancia)."""
    c = get_collection()
    if c.count() == 0:
        return []
    res = c.query(query_texts=[text], n_results=min(k, c.count()), where=where)
    out = []
    if res["documents"] and res["documents"][0]:
        for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append((d, m, dist))
    return out


def delete(where):
    try:
        get_collection().delete(where=where)
        return True
    except Exception:
        return False


def count():
    return get_collection().count()


def reset():
    global _col
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    _col = None
    get_collection()
