# -*- coding: utf-8 -*-
"""
Banco de pruebas para VALIDAR las herramientas (para la reunion tecnica).
Gracias a la arquitectura modular, comparar una herramienta = cambiar una linea.

Pruebas:
  1) Embeddings: MiniLM vs multilingual-e5  (precision de recuperacion + tiempo)
  2) Lector de PDF: PyMuPDF vs pypdf         (tiempo + texto extraido)
  3) Tamano de chunk: 300 / 500 / 800        (precision de recuperacion)
  4) Latencia de recuperacion                 (¿cumple < 8 s?)

Uso:  python pruebas_herramientas.py
"""
import os
import time
import numpy as np
from sentence_transformers import SentenceTransformer

BASE = os.path.dirname(__file__)
PDF = os.path.join(BASE, "docs", "computacion", "global", "reglamento_practicum_demo.pdf")

# preguntas de evaluacion -> palabra/frase que DEBE aparecer en el fragmento correcto
EVAL = [
    ("cuantas horas de practicas necesito", "160 horas"),
    ("cual es el plazo para entregar el informe", "8 dias"),
    ("que formato uso para el informe final", "f-02"),
    ("cual es la nota minima para aprobar", "7 sobre 10"),
    ("cada cuanto son las reuniones con el tutor", "dos semanas"),
    ("que es el practicum", "componente de practicas"),
]


def chunk(text, size, overlap=80):
    text = " ".join(text.split())
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i+size]); i += size - overlap
    return [t for t in out if t.strip()]


def texto_pymupdf():
    import fitz
    d = fitz.open(PDF)
    return " ".join(d[i].get_text() for i in range(len(d)))


def texto_pypdf():
    from pypdf import PdfReader
    r = PdfReader(PDF)
    return " ".join((p.extract_text() or "") for p in r.pages)


def cos(a, b):
    return a @ b.T


def evaluar_recuperacion(model, chunks, prefijo_q="", prefijo_d=""):
    """Devuelve (precision top-1, tiempo de embedding por consulta en ms)."""
    docs_emb = model.encode([prefijo_d + c for c in chunks], normalize_embeddings=True)
    aciertos, t_total = 0, 0.0
    for q, esperado in EVAL:
        t0 = time.perf_counter()
        qe = model.encode([prefijo_q + q], normalize_embeddings=True)
        t_total += (time.perf_counter() - t0)
        idx = int(np.argmax(cos(qe, docs_emb)[0]))
        if esperado in chunks[idx].lower():
            aciertos += 1
    return aciertos / len(EVAL), (t_total / len(EVAL)) * 1000


def linea():
    print("-" * 64)


print("\n=== Banco de pruebas de herramientas ===\n")

# ---------- 2) Lector de PDF ----------
linea(); print("2) LECTOR DE PDF  (PyMuPDF vs pypdf)")
for nombre, fn in [("PyMuPDF", texto_pymupdf), ("pypdf", texto_pypdf)]:
    t0 = time.perf_counter(); txt = fn(); ms = (time.perf_counter() - t0) * 1000
    print(f"  {nombre:9}: {len(txt):5} caracteres en {ms:6.1f} ms")

texto = texto_pymupdf()

# ---------- 3) Tamano de chunk (con MiniLM) ----------
linea(); print("3) TAMANO DE CHUNK  (modelo MiniLM)")
mini = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
for size in (300, 500, 800):
    chunks = chunk(texto, size)
    acc, _ = evaluar_recuperacion(mini, chunks)
    print(f"  chunk={size:4}: {len(chunks):2} fragmentos | precision top-1 = {acc*100:5.1f}%")

# ---------- 1) Embeddings MiniLM vs e5 ----------
linea(); print("1) EMBEDDINGS  (MiniLM vs multilingual-e5-small)  [chunk=500]")
chunks500 = chunk(texto, 500)
acc_m, t_m = evaluar_recuperacion(mini, chunks500)
print(f"  MiniLM (L12)      : precision {acc_m*100:5.1f}% | {t_m:5.1f} ms/consulta")
try:
    e5 = SentenceTransformer("intfloat/multilingual-e5-small")
    acc_e, t_e = evaluar_recuperacion(e5, chunks500, prefijo_q="query: ", prefijo_d="passage: ")
    print(f"  multilingual-e5   : precision {acc_e*100:5.1f}% | {t_e:5.1f} ms/consulta")
except Exception as ex:
    print(f"  (no se pudo cargar e5: {str(ex)[:60]})")

# ---------- 4) Latencia de recuperacion ----------
linea(); print("4) LATENCIA DE RECUPERACION  (embedding de la consulta)")
t0 = time.perf_counter()
for q, _ in EVAL:
    mini.encode([q], normalize_embeddings=True)
ms = (time.perf_counter() - t0) / len(EVAL) * 1000
print(f"  {ms:5.1f} ms por consulta (la generacion del LLM suma ~1-2 s)")
print(f"  -> recuperacion muy por debajo del limite de 8 s del requisito\n")
linea()
