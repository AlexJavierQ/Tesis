# -*- coding: utf-8 -*-
"""
INGESTA de documentos.

Convierte cada PDF en fragmentos ("chunks") de texto y los guarda en la base
vectorial. Este paso solo se ejecuta cuando se sube un documento nuevo o
cuando se quiere reindexar todo.

Estructura esperada de carpetas:
  datos/docs/<carrera>/global/*.pdf          -> reglamentos de la carrera
  datos/docs/<carrera>/cursos/<curso>/*.pdf  -> documentos de un curso
  .../_versiones/*.pdf                        -> versiones anteriores (no se indexan)
"""
import os
import glob
from nucleo import pdfreader, vectorstore, bd
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


def _scope(carrera, curso):
    return f"{carrera}|curso:{curso}" if curso else f"{carrera}|global"


def _carpeta(carrera, curso):
    return (os.path.join(DOCS, carrera, "cursos", curso) if curso
            else os.path.join(DOCS, carrera, "global"))


def _rel(path):
    """Ruta relativa a datos/docs/ (portable entre computadoras)."""
    return os.path.relpath(os.path.abspath(path), DOCS).replace("\\", "/")


def indexar_pdf(path, scope):
    """
    Trocea un PDF y guarda sus fragmentos en la base vectorial (ChromaDB).
    Primero borra los fragmentos anteriores del mismo archivo en ese ambito.
    Devuelve cuantos fragmentos indexo. (El catalogo de la BD se maneja aparte.)
    """
    nombre = os.path.basename(path)
    rel = _rel(path)
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


def guardar_documento(carrera, curso, nombre, contenido, usuario=None):
    """
    Guarda un PDF subido como NUEVA VERSION de su documento.
      - Si ya habia un archivo con ese nombre en el ambito, la version anterior
        se archiva en la subcarpeta _versiones/ (no se pierde).
      - El archivo vigente siempre queda con su nombre original, y es el unico
        que se indexa en ChromaDB.
      - Si el documento estaba DESACTIVADO, se guarda la version pero no se indexa.
    Devuelve {version, fragmentos, activo}.
    """
    carpeta = _carpeta(carrera, curso)
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, nombre)

    previo = bd.documento(carrera, curso, nombre)
    if previo and os.path.exists(destino):
        archivo = os.path.join(carpeta, "_versiones",
                               f"{os.path.splitext(nombre)[0]}_v{previo['version']}.pdf")
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        os.replace(destino, archivo)
        bd.mover_version(previo["ruta"], _rel(archivo))

    with open(destino, "wb") as f:
        f.write(contenido)

    activo = previo["activo"] if previo else True
    n = indexar_pdf(destino, _scope(carrera, curso)) if activo else 0
    version = bd.registrar_version(carrera, curso, nombre, _rel(destino), n, usuario)
    return {"version": version, "fragmentos": n, "activo": activo}


def cambiar_estado(doc_id, activo):
    """
    Activa o desactiva un documento.
      desactivar -> se quitan sus fragmentos de ChromaDB (el chat deja de usarlo)
      activar    -> se vuelve a indexar su version vigente
    """
    d = bd.documento_por_id(doc_id)
    if not d:
        raise ValueError("Documento no encontrado.")
    scope = _scope(d["carrera"], d["curso"])
    bd.cambiar_estado_documento(doc_id, activo)
    if activo:
        n = indexar_pdf(os.path.join(DOCS, d["ruta"]), scope)
        bd.actualizar_fragmentos(d["ruta"], n)
    else:
        vectorstore.borrar({"$and": [{"fuente": d["nombre"]}, {"scope": scope}]})


def borrar_documento(doc_id):
    """Elimina un documento: sus fragmentos, sus archivos (todas las versiones) y su registro."""
    d = bd.documento_por_id(doc_id)
    if not d:
        raise ValueError("Documento no encontrado.")
    vectorstore.borrar({"$and": [{"fuente": d["nombre"]},
                                 {"scope": _scope(d["carrera"], d["curso"])}]})
    for ruta in bd.borrar_documento(doc_id):
        archivo = os.path.join(DOCS, ruta)
        if os.path.exists(archivo):
            os.remove(archivo)
    return d


def _indexar_y_registrar(path, carrera, curso):
    """Para indexar_todo: indexa un PDF (si no esta desactivado) y lo asegura en el catalogo."""
    rel = _rel(path)
    if bd.esta_inactivo(rel):
        return 0
    n = indexar_pdf(path, _scope(carrera, curso))
    if bd.documento(carrera, curso, os.path.basename(path)):
        bd.actualizar_fragmentos(rel, n)
    else:
        bd.registrar_version(carrera, curso, os.path.basename(path), rel, n)
    return n


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
            n = _indexar_y_registrar(p, carrera, None)
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
                    n = _indexar_y_registrar(p, carrera, curso)
                    total += n
                    print(f"  [{carrera}|curso:{curso}] {os.path.basename(p)}: {n} fragmentos")
    print(f"\nListo. {total} fragmentos indexados en total.")


if __name__ == "__main__":
    indexar_todo()
