# -*- coding: utf-8 -*-
"""
ADAPTADOR de lectura de PDF.

Se usa PyMuPDF (importado como 'fitz') porque:
  - extrae el mismo texto que pypdf pero ~2.3 veces mas rapido
  - da el TAMANO y el ESTILO de cada linea, lo que permite reconocer titulos
  - puede rasterizar cada pagina en imagen (visor de citas)

Ademas de leer pagina por pagina, este modulo divide el documento en
SECCIONES (titulo + contenido). Un titulo se reconoce por su forma, no por
su texto, asi sirve para cualquier documento:
  - letra claramente mas grande que el cuerpo (p. ej. 16 pt vs 11 pt), o
  - negrita y empieza con un numero de seccion ("8.2 Practicum 2 ...").
Se descartan los encabezados/pies que se repiten en muchas paginas y las
lineas del indice ("Objetivo ........ 5").
"""
import re
from collections import Counter

import fitz  # PyMuPDF

NUMERO_SECCION = re.compile(r"^\d{1,2}(\.\d{1,2}){0,3}\.?\s+\S")
SOLO_NUMERO = re.compile(r"^\d{1,2}(\.\d{1,2}){0,3}\.?$")   # "8.1" en su propia linea
EMPIEZA_CON_LETRA = re.compile(r"^[A-Za-zÁÉÍÓÚÑáéíóúñ]")
LINEA_INDICE = re.compile(r"\.{5,}\s*\d*\s*$")
MAX_TITULO = 120          # un titulo mas largo que esto es un parrafo
REPETICION_PIE = 0.4      # linea presente en >=40 % de paginas = encabezado/pie


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


# ---------- lectura por secciones ----------
def _celda(texto):
    """Limpia una celda: une palabras partidas por el ancho de columna ("preprofesionale\\ns")."""
    partes = (texto or "").split("\n")
    salida = partes[0]
    for p in partes[1:]:
        salida += p if len(p.strip()) <= 2 and p.strip().islower() else " " + p
    return " ".join(salida.split())


def _filas_de_tabla(tabla):
    """Una tabla como lineas de texto, fila por fila: 'celda | celda | celda'."""
    filas = []
    for fila in tabla.extract():
        celdas = []
        for c in fila:
            c = _celda(c)
            if c and (not celdas or celdas[-1] != c):
                celdas.append(c)
        if celdas:
            filas.append(" | ".join(celdas))
    return filas


def _lineas(doc):
    """
    Cada linea con texto: (pagina, bloque, texto, tamano, fraccion_en_negrita).
    Las tablas se leen FILA POR FILA (la lectura normal las mezcla por columnas):
    el texto que cae dentro de una tabla se reemplaza por sus filas. Las filas
    llevan tamano -1 para que nunca se tomen como titulos.
    """
    salida = []
    for n, pagina in enumerate(doc, start=1):
        try:
            tablas = pagina.find_tables().tables
        except Exception:
            tablas = []
        dentro = lambda x, y: any(t.bbox[0] <= x <= t.bbox[2] and t.bbox[1] <= y <= t.bbox[3]
                                  for t in tablas)
        items = []   # (y, x, tupla) para ordenar lineas y filas de tabla por posicion
        for b, bloque in enumerate(pagina.get_text("dict")["blocks"]):
            for linea in bloque.get("lines", []):
                spans = [s for s in linea["spans"] if s["text"].strip()]
                if not spans:
                    continue
                x0, y0, x1, y1 = linea["bbox"]
                if dentro((x0 + x1) / 2, (y0 + y1) / 2):
                    continue
                texto = " ".join("".join(s["text"] for s in linea["spans"]).split())
                total = sum(len(s["text"].strip()) for s in spans)
                negrita = sum(len(s["text"].strip()) for s in spans
                              if "Bold" in s["font"] or s["flags"] & 16) / max(1, total)
                items.append((y0, x0, (n, b, texto, max(s["size"] for s in spans), negrita)))
        for i, t in enumerate(tablas):
            for j, fila in enumerate(_filas_de_tabla(t)):
                items.append((t.bbox[1] + j * 0.01, t.bbox[0], (n, f"t{i}.{j}", fila, -1, 0)))
        if tablas:
            items.sort(key=lambda it: (round(it[0], 2), it[1]))
        salida.extend(it[2] for it in items)
    return salida


def _repetidas(lineas, paginas):
    """Lineas que aparecen en muchas paginas (encabezados y pies), sin contar numeros."""
    if paginas < 3:
        return set()
    clave = lambda t: re.sub(r"\d+", "#", t)
    vistas = Counter()
    for pag in range(1, paginas + 1):
        vistas.update({clave(t) for (n, _, t, _, _) in lineas if n == pag})
    return {k for k, v in vistas.items() if v >= REPETICION_PIE * paginas}


def secciones(path):
    """
    Divide el PDF en secciones: [{titulo, pagina, parrafos: [(pagina, texto)]}].
    Un parrafo es un bloque de texto del PDF. El texto anterior al primer
    titulo queda en una seccion con titulo vacio.
    """
    doc = fitz.open(path)
    lineas = _lineas(doc)
    if not lineas:
        return []
    repetidas = _repetidas(lineas, doc.page_count)
    clave = lambda t: re.sub(r"\d+", "#", t)

    # tamano del cuerpo = el mas frecuente, ponderado por cantidad de texto
    tamanos = Counter()
    for (_, _, t, tam, _) in lineas:
        if tam > 0:
            tamanos[round(tam)] += len(t)
    cuerpo = tamanos.most_common(1)[0][0] if tamanos else 10

    def es_titulo(texto, tam, negrita):
        if tam < 0 or len(texto) > MAX_TITULO or LINEA_INDICE.search(texto):
            return False
        return tam >= cuerpo + 2.5 or (negrita >= 0.6 and NUMERO_SECCION.match(texto) is not None)

    # paginas del indice (varias lineas "Titulo ....... 12"): se omiten enteras
    indice = Counter(n for (n, _, t, _, _) in lineas if LINEA_INDICE.search(t))
    paginas_indice = {n for n, veces in indice.items() if veces >= 3}

    resultado = [{"titulo": "", "pagina": 1, "parrafos": []}]
    ultimo = None   # (pagina, bloque) del ultimo parrafo, para unir lineas del mismo bloque
    titulo_anterior = None   # (pagina, bloque) del ultimo titulo, para titulos en dos lineas
    numero = None   # numero de seccion en negrita que espera su titulo en la linea siguiente
    for (n, b, texto, tam, negrita) in lineas:
        if n in paginas_indice or LINEA_INDICE.search(texto):
            continue
        # "8.1" sola en negrita: el titulo viene en la siguiente linea del mismo bloque
        # (se mira antes que los repetidos: los numeros de pagina no van en negrita)
        if negrita >= 0.6 and SOLO_NUMERO.match(texto):
            numero = (n, b, texto.rstrip("."))
            continue
        if clave(texto) in repetidas:
            continue
        if numero and numero[:2] == (n, b) and negrita >= 0.6 and EMPIEZA_CON_LETRA.match(texto):
            texto = f"{numero[2]} {texto}"
        elif numero:
            # no era un numero de seccion: se conserva como texto (no se pierde el dato)
            resultado[-1]["parrafos"].append((numero[0], numero[2]))
        numero = None
        if texto.isdigit():           # numero de pagina suelto
            continue
        if es_titulo(texto, tam, negrita):
            if titulo_anterior == (n, b) and not resultado[-1]["parrafos"]:
                resultado[-1]["titulo"] += " " + texto          # titulo en dos lineas
            else:
                resultado.append({"titulo": texto, "pagina": n, "parrafos": []})
            titulo_anterior, ultimo = (n, b), None
            continue
        titulo_anterior = None
        parrafos = resultado[-1]["parrafos"]
        if parrafos and ultimo == (n, b):
            parrafos[-1] = (parrafos[-1][0], parrafos[-1][1] + " " + texto)
        else:
            parrafos.append((n, texto))
        ultimo = (n, b)

    secciones_con_texto = [s for s in resultado if s["parrafos"]]
    _agregar_rutas(resultado, secciones_con_texto)
    return secciones_con_texto


def _numero(titulo):
    m = re.match(r"^(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s", titulo or "")
    return m.group(1) if m else None


def _agregar_rutas(todas, con_texto):
    """
    A cada seccion numerada le agrega su RUTA de titulos: "14 Evidencias ... ›
    14.2 Practicas de insercion ...". Asi un fragmento de la 14.2 tambien
    "sabe" que trata de evidencias aunque esa palabra solo este en el titulo
    padre (que puede no tener texto propio).
    """
    titulos = {}                       # numero -> titulo, segun aparecen
    for s in todas:
        n = _numero(s["titulo"])
        if n:
            titulos[n] = s["titulo"]
        s["ruta"] = s["titulo"]
        # solo la seccion principal + la propia: una ruta mas larga le quitaria
        # espacio al texto en el fragmento (el modelo de embeddings lee ~680 caracteres)
        principal = titulos.get(n.split(".")[0]) if n and "." in n else None
        if principal:
            s["ruta"] = f"{principal} › {s['titulo']}"
