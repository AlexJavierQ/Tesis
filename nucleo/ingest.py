# -*- coding: utf-8 -*-
"""
Pipeline de ingesta (C1). Usa los adaptadores pdfreader + vectorstore.
  docs/<carrera>/global/*.pdf          -> scope "<carrera>|global"
  docs/<carrera>/cursos/<curso>/*.pdf  -> scope "<carrera>|curso:<curso>"

Uso:  python ingest.py     (reconstruye todo el indice)
"""
import os
import glob
import re
from nucleo import pdfreader
from nucleo import vectorstore
from nucleo.rag import DOCS

CHUNK_SIZE = 500
OVERLAP = 80

# Avisos y pies que se repiten en TODOS los documentos. Si se indexan, compiten
# con el contenido real en cualquier consulta (y como aparecen en cada archivo,
# empatan siempre). Se quitan del texto ANTES de trocear: filtrarlos despues no
# basta, porque se fusionan con el encabezado en un bloque mas grande.
RUIDO = (
    r"AVISO:.*?(?:institucion|instituci[oó]n)\.",
    r"documento ficticio[^.]*\.",
    r"No es normativa oficial[^.]*\.",
)

# Inicio de unidad normativa: "Articulo 12.", "1. HORAS", "TITULO IV"
_UNIDAD = re.compile(
    r"(?=^\s*(?:art[ií]culo\s+\d+|t[ií]tulo\s+[IVXLC]+|cap[ií]tulo\s+[IVXLC\d]+|\d+\.\s+[A-ZÁÉÍÓÚÑ]))",
    re.IGNORECASE | re.MULTILINE,
)


def limpiar_ruido(text):
    """Quita avisos y pies repetidos antes de trocear."""
    for patron in RUIDO:
        text = re.sub(patron, " ", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def bloques_semanticos(text):
    """
    Parte el texto por unidades con sentido propio (articulo, titulo, parrafo)
    en vez de cada N caracteres.

    El corte ciego por caracteres partia articulos a la mitad y, con el solape,
    generaba fragmentos vecinos casi identicos que se agolpaban en el top-k y
    expulsaban al fragmento correcto.
    """
    partes = [p for p in _UNIDAD.split(text) if p.strip()]
    if len(partes) <= 1:
        # documento sin estructura numerada: se cae a parrafos
        partes = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [" ".join(p.split()) for p in partes]


def chunk_text(text, size=CHUNK_SIZE, overlap=OVERLAP):
    """
    Agrupa bloques semanticos en fragmentos de hasta `size` caracteres sin
    partir un bloque. Solo se trocea por caracteres un bloque que por si solo
    exceda el limite, y ahi si se aplica solape para no perder el empalme.
    """
    fragmentos, actual = [], ""
    for bloque in bloques_semanticos(limpiar_ruido(text)):
        if len(bloque) < 25:                         # restos sueltos del limpiado
            continue
        if len(bloque) > size:                       # bloque largo: se trocea
            if actual:
                fragmentos.append(actual)
                actual = ""
            i = 0
            while i < len(bloque):
                fragmentos.append(bloque[i:i + size])
                i += size - overlap
        elif len(actual) + len(bloque) + 1 <= size:  # cabe: se acumula
            actual = f"{actual} {bloque}".strip()
        else:                                        # no cabe: se cierra
            fragmentos.append(actual)
            actual = bloque
    if actual:
        fragmentos.append(actual)
    return [f for f in fragmentos if f.strip()]


def add_pdf(path, scope, chunk_size=CHUNK_SIZE, overlap=OVERLAP):
    nombre = os.path.basename(path)
    # Se guarda la ruta RELATIVA a docs/, no la absoluta: un indice con rutas
    # absolutas solo sirve en la maquina donde se creo (y filtra el arbol de
    # directorios del equipo al cliente).
    rel = os.path.relpath(os.path.abspath(path), DOCS).replace("\\", "/")
    vectorstore.delete({"$and": [{"fuente": nombre}, {"scope": scope}]})
    docs, metas, ids = [], [], []
    for pg, texto in enumerate(pdfreader.paginas_texto(path), start=1):
        for j, trozo in enumerate(chunk_text(texto, chunk_size, overlap)):
            docs.append(trozo)
            metas.append({"fuente": nombre, "pagina": pg, "scope": scope, "path": rel})
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
