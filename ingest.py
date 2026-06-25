# -*- coding: utf-8 -*-
"""
Pipeline de ingesta (C1). Usa los adaptadores pdfreader + vectorstore.
  docs/<carrera>/global/*.pdf          -> scope "<carrera>|global"
  docs/<carrera>/cursos/<curso>/*.pdf  -> scope "<carrera>|curso:<curso>"

Uso:  python ingest.py     (reconstruye todo el indice)
"""
import os
import glob
import pdfreader
import vectorstore
from rag import DOCS

CHUNK_SIZE = 500
OVERLAP = 80


def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    text = " ".join(text.split())
    trozos, i = [], 0
    while i < len(text):
        trozos.append(text[i:i + size])
        i += size - overlap
    return [t for t in trozos if t.strip()]


def add_pdf(path, scope, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    nombre = os.path.basename(path)
    abspath = os.path.abspath(path)
    vectorstore.delete({"$and": [{"fuente": nombre}, {"scope": scope}]})
    docs, metas, ids = [], [], []
    for pg, texto in enumerate(pdfreader.paginas_texto(path), start=1):
        for j, trozo in enumerate(chunk_text(texto, chunk_size, overlap)):
            docs.append(trozo)
            metas.append({"fuente": nombre, "pagina": pg, "scope": scope, "path": abspath})
            ids.append(f"{scope}|{nombre}|{pg}|{j}")
    vectorstore.add(docs, metas, ids)
    return len(docs)


def remove_doc(nombre, scope):
    return vectorstore.delete({"$and": [{"fuente": nombre}, {"scope": scope}]})


def main():
    os.makedirs(DOCS, exist_ok=True)
    vectorstore.reset()
    total = 0
    for carrera in sorted(os.listdir(DOCS)):
        cdir = os.path.join(DOCS, carrera)
        if not os.path.isdir(cdir):
            continue
        for p in glob.glob(os.path.join(cdir, "global", "*.pdf")):
            n = add_pdf(p, f"{carrera}|global"); total += n
            print(f"  [{carrera}|global] {os.path.basename(p)}: {n}")
        for cu in glob.glob(os.path.join(cdir, "cursos", "*")):
            if os.path.isdir(cu):
                curso = os.path.basename(cu)
                for p in glob.glob(os.path.join(cu, "*.pdf")):
                    n = add_pdf(p, f"{carrera}|curso:{curso}"); total += n
                    print(f"  [{carrera}|curso:{curso}] {os.path.basename(p)}: {n}")
    print(f"Listo. {total} fragmentos indexados.")


if __name__ == "__main__":
    main()
