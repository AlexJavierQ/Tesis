# -*- coding: utf-8 -*-
"""
INGESTA de documentos.

Convierte cada PDF en fragmentos ("chunks") de texto y los guarda en la base
vectorial. Este paso solo se ejecuta cuando se sube un documento nuevo o
cuando se quiere reindexar todo.

Estructura esperada de carpetas:
  datos/docs/<carrera>/global/*.pdf          -> reglamentos de la carrera
  datos/docs/<carrera>/cursos/<curso>/*.pdf  -> documentos de un curso
"""
import os
import glob
from nucleo import pdfreader, vectorstore
from nucleo.rag import DOCS

TAMANO = 500   # caracteres por fragmento
SOLAPE = 80    # caracteres compartidos entre fragmentos vecinos (para no cortar frases)


def trocear(texto):
    """
    Parte el texto en trozos de ~TAMANO caracteres, con SOLAPE entre trozos.
    El solape asegura que si una frase importante cae entre dos trozos, al
    menos uno de los dos la contendra entera.
    """
    texto = " ".join(texto.split())  # colapsa espacios y saltos de linea
    trozos, i = [], 0
    while i < len(texto):
        trozos.append(texto[i:i + TAMANO])
        i += TAMANO - SOLAPE
    return [t for t in trozos if t.strip()]


def indexar_pdf(path, scope):
    """
    Trocea un PDF y lo guarda en la base vectorial.
    Primero borra fragmentos anteriores del mismo archivo (si es reindexado).
    Devuelve cuantos fragmentos indexo.
    """
    nombre = os.path.basename(path)
    # ruta relativa a datos/docs/, para que el indice sea portable
    rel = os.path.relpath(os.path.abspath(path), DOCS).replace("\\", "/")

    # borra lo que hubiera de este mismo archivo en este scope
    vectorstore.borrar({"$and": [{"fuente": nombre}, {"scope": scope}]})

    textos, metadatos, ids = [], [], []
    for num_pag, texto_pag in enumerate(pdfreader.paginas_texto(path), start=1):
        for j, trozo in enumerate(trocear(texto_pag)):
            textos.append(trozo)
            metadatos.append({
                "fuente": nombre,
                "pagina": num_pag,
                "scope": scope,
                "path": rel,
            })
            ids.append(f"{scope}|{nombre}|{num_pag}|{j}")
    if textos:
        vectorstore.agregar(textos, metadatos, ids)
    return len(textos)


def borrar_documento(nombre, scope):
    """Elimina todos los fragmentos de un archivo concreto."""
    vectorstore.borrar({"$and": [{"fuente": nombre}, {"scope": scope}]})


def indexar_todo():
    """Recorre datos/docs/ e indexa todos los PDF que encuentre."""
    if not os.path.isdir(DOCS):
        print(f"No existe la carpeta {DOCS}")
        return
    total = 0
    for carrera in sorted(os.listdir(DOCS)):
        cdir = os.path.join(DOCS, carrera)
        if not os.path.isdir(cdir):
            continue
        # reglamentos generales de la carrera
        for p in glob.glob(os.path.join(cdir, "global", "*.pdf")):
            n = indexar_pdf(p, f"{carrera}|global")
            total += n
            print(f"  [{carrera}|global] {os.path.basename(p)}: {n} fragmentos")
        # documentos por curso
        cursos_dir = os.path.join(cdir, "cursos")
        if os.path.isdir(cursos_dir):
            for curso in sorted(os.listdir(cursos_dir)):
                cu = os.path.join(cursos_dir, curso)
                if not os.path.isdir(cu):
                    continue
                for p in glob.glob(os.path.join(cu, "*.pdf")):
                    n = indexar_pdf(p, f"{carrera}|curso:{curso}")
                    total += n
                    print(f"  [{carrera}|curso:{curso}] {os.path.basename(p)}: {n} fragmentos")
    print(f"\nListo. {total} fragmentos indexados en total.")


if __name__ == "__main__":
    indexar_todo()
