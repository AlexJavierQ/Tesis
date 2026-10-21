# -*- coding: utf-8 -*-
"""
BUSQUEDA HIBRIDA: por significado (vectores) + por palabras (BM25).

Por que: el modelo de embeddings (MiniLM) a veces confunde frases parecidas.
Ejemplo real: "que evidencias se presentan en las practicas de insercion al
entorno laboral" traia primero un diagrama que repite "practicas laborales",
y la seccion correcta (14.2, la lista de evidencias) quedaba en el puesto 12.
Una busqueda por palabras clave la encuentra enseguida porque contiene
"evidencias" e "insercion".

Como se combinan (Reciprocal Rank Fusion, RRF):
  puntaje = 1/(60 + puesto en vectores) + 1/(60 + puesto en BM25)
Un fragmento bien ubicado en las dos listas sube; uno que solo aparece en una
tambien puede entrar. El 60 es la constante habitual de RRF.

Anti-alucinacion: a TODOS los candidatos (vengan de vectores o de BM25) se les
calcula su distancia semantica a la pregunta, y el umbral de similitud se
sigue aplicando igual. BM25 ayuda a ORDENAR, no deja pasar texto que no se
parezca a la pregunta.
"""
import math
import re
import unicodedata
from collections import Counter

import numpy as np

from nucleo import vectorstore, embeddings

K1, B = 1.5, 0.75     # parametros estandar de BM25
RRF_K = 60            # constante de Reciprocal Rank Fusion
CANDIDATOS = 20       # cuantos candidatos aporta cada busqueda

PALABRAS_VACIAS = set("""
a al algo algun alguna como con cual cuales cuando de del desde donde el ella en entre
es esa ese eso esta este esto estos fue ha hay la las le les lo los mas me mi mis muy
no nos o para pero por que se segun ser si sin sobre su sus te tiene tu un una uno unos
y ya puedo debo cuanto cuanta cuantos cuantas
""".split())

_indices = {}   # scope -> (cantidad de fragmentos al construirlo, indice)


def _palabras(texto):
    """Minusculas, sin tildes, sin palabras vacias ni palabras muy cortas."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return [p for p in re.findall(r"[a-z0-9]+", t) if len(p) > 2 and p not in PALABRAS_VACIAS]


class _BM25:
    """Indice BM25 de los fragmentos de un ambito."""

    def __init__(self, ids, textos):
        self.ids = ids
        self.docs = [Counter(_palabras(t)) for t in textos]
        self.largos = [sum(d.values()) for d in self.docs]
        self.promedio = sum(self.largos) / max(1, len(self.largos))
        aparece = Counter(p for d in self.docs for p in d)
        n = len(self.docs)
        self.idf = {p: math.log(1 + (n - f + 0.5) / (f + 0.5)) for p, f in aparece.items()}

    def puntajes(self, pregunta):
        """{id: puntaje BM25} de los fragmentos que comparten alguna palabra con la pregunta."""
        q = _palabras(pregunta)
        salida = {}
        for i, d in enumerate(self.docs):
            s = 0.0
            for p in q:
                f = d.get(p, 0)
                if f:
                    s += self.idf[p] * f * (K1 + 1) / (f + K1 * (1 - B + B * self.largos[i] / self.promedio))
            if s > 0:
                salida[self.ids[i]] = s
        return salida


def _indice(scope):
    """Indice BM25 del ambito; se reconstruye si cambio la cantidad de fragmentos."""
    col = vectorstore.coleccion()
    total = col.count()
    guardado = _indices.get(scope)
    if guardado and guardado[0] == total:
        return guardado[1]
    datos = col.get(where={"scope": scope}, include=["documents"])
    indice = _BM25(datos["ids"], datos["documents"])
    _indices[scope] = (total, indice)
    return indice


def buscar(pregunta, scope, k):
    """
    Los k fragmentos mas relevantes del ambito, combinando vectores y BM25.
    Cada uno: {texto, meta, distancia} (distancia coseno a la pregunta).
      1. candidatos = los CANDIDATOS mejores por vectores + los mejores por BM25
      2. a TODOS se les calcula su distancia semantica y su puntaje BM25
      3. se ordenan por RRF usando el puesto de cada uno en ambos criterios
      4. se deja un fragmento por seccion (la seccion completa la lee el modelo)
    """
    por_vector = vectorstore.buscar(pregunta, k=CANDIDATOS, filtro={"scope": scope})
    bm25 = _indice(scope).puntajes(pregunta)
    por_palabra = sorted(bm25, key=bm25.get, reverse=True)[:CANDIDATOS]

    # datos de los candidatos que solo encontro BM25 (texto, metadatos y su vector)
    hits = {h["meta"]["_id"]: h for h in por_vector}
    faltan = [vid for vid in por_palabra if vid not in hits]
    if faltan:
        datos = vectorstore.coleccion().get(ids=faltan, include=["documents", "metadatas", "embeddings"])
        q = np.asarray(embeddings.embed([pregunta])[0])
        for vid, texto, meta, vec in zip(datos["ids"], datos["documents"],
                                         datos["metadatas"], datos["embeddings"]):
            v = np.asarray(vec)
            coseno = float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v)))
            hits[vid] = {"texto": texto, "meta": {**meta, "_id": vid}, "distancia": 1 - coseno}

    # puesto de cada candidato en los dos criterios (dentro del conjunto de candidatos)
    puesto_vec = {vid: i for i, vid in enumerate(sorted(hits, key=lambda v: hits[v]["distancia"]))}
    puesto_bm25 = {vid: i for i, vid in enumerate(sorted(hits, key=lambda v: -bm25.get(v, 0)))}
    puntaje = lambda vid: 1 / (RRF_K + puesto_vec[vid]) + 1 / (RRF_K + puesto_bm25[vid])

    salida, secciones = [], set()
    for vid in sorted(hits, key=puntaje, reverse=True):
        m = hits[vid]["meta"]
        seccion = (m.get("documento_id"), m.get("contexto") or vid)
        if seccion in secciones:
            continue
        secciones.add(seccion)
        salida.append(hits[vid])
        if len(salida) >= k:
            break
    return salida
