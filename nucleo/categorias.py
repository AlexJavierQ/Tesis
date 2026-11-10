# -*- coding: utf-8 -*-
"""
CATEGORIAS CONTROLADAS de las consultas (para la analitica).

El panel de metricas no guarda ni muestra la pregunta literal: cada consulta
se reduce a UNA categoria de un vocabulario cerrado. La clasificacion es por
palabras clave, deterministica y sin llamar al modelo de lenguaje: se puede
explicar y repetir, y la pregunta nunca sale del proceso.

Es una heuristica sencilla: su precision NO esta evaluada. Lo que no encaja
en ninguna categoria cae en "otros".

El vocabulario esta repetido en el CHECK de la tabla consulta_eventos
(nucleo/bd.py); una prueba verifica que ambos coincidan.
"""
import re
import unicodedata

# clave -> (etiqueta para el panel, raices de palabras que la identifican)
CATEGORIAS = {
    "horas": ("Horas y duración",
              ("hora", "duracion", "dura ", "duran ", "cuanto tiempo", "jornada", "creditos")),
    "plazos": ("Plazos y fechas",
               ("plazo", "fecha", "cuando", "calendario", "cronograma", "limite",
                "hasta que dia", "periodo", "semana")),
    "formatos": ("Formatos, informes y evidencias",
                 ("formato", "informe", "evidencia", "plantilla", "anexo", "bitacora",
                  "portafolio", "carta", "certificado", "documento")),
    "evaluacion": ("Evaluación y calificaciones",
                   ("evalua", "nota", "calific", "pondera", "rubrica", "aprob",
                    "recuperacion", "reprob", "supletorio", "puntaje")),
    "requisitos": ("Requisitos",
                   ("requisito", "prerrequisito", "necesito", "que se necesita", "puedo",
                    "debo cumplir", "condicion", "matricul")),
    "tramites": ("Trámites, plazas y convenios",
                 ("tramite", "postul", "solicitud", "solicitar", "convenio", "empresa",
                  "plaza", "inscrib", "convalid", "homolog", "validar", "tutor")),
    "otros": ("Otros temas", ()),
}
CLAVES = tuple(CATEGORIAS)


def _normalizar(texto):
    """Minusculas, sin tildes y sin signos: "¿Cuántas HORAS?" -> "cuantas horas"."""
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return " " + re.sub(r"[^a-z0-9ñ ]+", " ", t) + " "


def clasificar(pregunta):
    """
    Categoria de una pregunta: la que mas palabras clave reune. Con empate
    gana la primera en el orden de CATEGORIAS; sin coincidencias, "otros".
    Cada raiz se busca al INICIO de una palabra ("hora" no coincide con "ahora").
    """
    t = _normalizar(pregunta)
    mejor, puntos = "otros", 0
    for clave, (_, raices) in CATEGORIAS.items():
        n = sum(1 for r in raices if " " + r in t)
        if n > puntos:
            mejor, puntos = clave, n
    return mejor


def etiqueta(clave):
    return CATEGORIAS.get(clave, CATEGORIAS["otros"])[0]
