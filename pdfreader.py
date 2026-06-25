# -*- coding: utf-8 -*-
"""
ADAPTADOR de lectura de PDF. Aísla PyMuPDF (fitz).
Para cambiar a otra librería (pypdf, etc.) solo reimplementas estas funciones.
"""
import fitz


def paginas_texto(path):
    """Lista con el texto de cada página."""
    doc = fitz.open(path)
    return [doc[i].get_text() for i in range(len(doc))]


def num_paginas(path):
    return len(fitz.open(path))


def render_png(path, pagina, dpi=135):
    """Renderiza una página como PNG (bytes) para el visor."""
    doc = fitz.open(path)
    idx = max(0, min(int(pagina) - 1, len(doc) - 1))
    return doc[idx].get_pixmap(dpi=dpi).tobytes("png")
