# -*- coding: utf-8 -*-
"""
ADAPTADOR de lectura de PDF.

Se usa PyMuPDF (importado como 'fitz') porque:
  - extrae el mismo texto que pypdf pero ~2.3 veces mas rapido (ver
    documentacion/RESULTADOS_PRUEBAS.md)
  - puede rasterizar cada pagina en imagen (lo usamos en el visor de citas)
"""
import fitz  # PyMuPDF


def paginas_texto(path):
    """Devuelve una lista con el texto de cada pagina del PDF."""
    doc = fitz.open(path)
    return [doc[i].get_text() for i in range(len(doc))]


def num_paginas(path):
    """Cuantas paginas tiene el PDF."""
    return fitz.open(path).page_count


def render_png(path, pagina, dpi=135):
    """Convierte una pagina en imagen PNG (bytes). La usa el visor de citas."""
    doc = fitz.open(path)
    p = doc[max(0, min(pagina - 1, doc.page_count - 1))]
    return p.get_pixmap(dpi=dpi).tobytes("png")
