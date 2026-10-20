# -*- coding: utf-8 -*-
"""
MEDICION DEL COSTO DE LA MEMORIA CONVERSACIONAL.

Compara las dos estrategias de nucleo/memoria.py sobre las MISMAS
conversaciones guionadas:
  - concatenacion (original): pega la pregunta anterior si parece seguimiento.
  - resumen (actual): ventana reciente + resumen + reescritura con el modelo.

Por cada turno se registra:
  - llamadas al modelo y su proposito (respuesta / reescritura / resumen)
  - tokens de entrada y de salida (los reporta Groq en `usage`)
  - tiempo total del turno y tiempo de cada llamada (sin contar las esperas
    por limite de peticiones, que se reportan aparte)
  - pregunta interpretada y si la respuesta contiene el dato esperado
    (acierto aproximado por palabra clave)

Uso:
    python -m evaluacion.medir_memoria                 # 1 repeticion
    python -m evaluacion.medir_memoria --repeticiones 2 --pausa 15

Salida: evaluacion/resultados_memoria.md y evaluacion/resultados_memoria.json
Requiere GROQ_API_KEY. No registra metricas de uso (llama al nucleo directo).
"""
import os
import sys
import json
import time
import argparse
import statistics
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import config  # noqa: F401  (carga la key)
from nucleo import rag, llm, memoria, historial, parametros

CARRERA, CURSO, MODO_RESPUESTA = "computacion", "Practicum 2", "ambos"
USUARIO = "estudiante"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_memoria")

# (pregunta, palabras clave esperadas en la respuesta o None si no se evalua)
CONVERSACIONES = [
    {"nombre": "Horas y entrega del informe", "turnos": [
        ("¿Cuántas horas de prácticas necesito en total?", ["240"]),
        ("¿Y cuántas corresponden al Prácticum 2?", ["120", "144"]),
        ("Ya llevo 60 horas en una empresa de software.", None),
        ("¿Cuál es el plazo para entregar el informe cuando termine?", ["8 dias", "ocho"]),
        ("¿Qué formato uso para eso?", ["f-02"]),
        ("¿Y quién lo evalúa?", ["tutor"]),
        ("¿Qué nota necesito para aprobar?", ["7"]),
    ]},
    {"nombre": "Actores de la práctica (referencia lejana)", "turnos": [
        ("¿Qué es un practicante preprofesional?", ["remuneracion", "fines educativos", "formacion"]),
        ("¿Y en qué se diferencia de un pasante?", ["pasant"]),
        ("¿Cuáles son las funciones del tutor externo?", ["evalua", "asistencia", "tutelar"]),
        ("¿Y las del tutor académico?", ["planificacion", "seguimiento", "orientar"]),
        ("Volviendo a lo primero, ¿esa figura recibe algún pago?", ["sin recibir", "no recibe", "remuneracion"]),
        ("¿Hasta cuándo puedo postular a una plaza?", ["28"]),
        ("¿Y quién tiene que validar esa postulación?", ["docente"]),
    ]},
]


def _normal(texto):
    """Minusculas, sin tildes, y espacios/guiones 'raros' del modelo como normales
    (escribe '8 dias' o 'F‑02' con espacio y guion de no separacion)."""
    t = unicodedata.normalize("NFKD", (texto or "").lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in t)
    return "".join("-" if unicodedata.category(ch) == "Pd" else ch for ch in t)


def _acierto(respuesta, esperadas):
    if esperadas is None:
        return None
    r = _normal(respuesta)
    return any(_normal(e) in r for e in esperadas)


def correr_conversacion(modo, conv, repeticion, pausa):
    """Ejecuta una conversacion completa con un modo de memoria. Devuelve filas por turno."""
    filas = []
    cid = historial.crear_conversacion(USUARIO, f"[medicion] {conv['nombre']}")
    try:
        for n, (pregunta, esperadas) in enumerate(conv["turnos"], start=1):
            inicio = time.perf_counter()
            with llm.medir() as llamadas:
                contexto = memoria.preparar(cid)
                r = rag.responder(pregunta, CARRERA, CURSO, contexto, MODO_RESPUESTA)
            total = time.perf_counter() - inicio
            espera = sum(l["espera_limite"] for l in llamadas)
            citas = [{"fuente": c["fuente"], "pagina": c["pagina"]} for c in r["citas"]]
            historial.agregar_mensaje(cid, "user", pregunta)
            historial.agregar_mensaje(cid, "bot", r["respuesta"], citas)
            filas.append({
                "modo": modo, "conversacion": conv["nombre"], "repeticion": repeticion,
                "turno": n, "pregunta": pregunta,
                "interpretada": r["pregunta_interpretada"],
                "con_respaldo": r["con_respaldo"],
                "acierto": _acierto(r["respuesta"], esperadas),
                "respuesta": r["respuesta"],
                "llamadas": llamadas,
                "n_llamadas": len(llamadas),
                "tokens_entrada": sum(l["tokens_entrada"] for l in llamadas),
                "tokens_salida": sum(l["tokens_salida"] for l in llamadas),
                "segundos": round(total - espera, 3),        # sin esperas por limite
                "espera_limite": round(espera, 3),
                "fallos_llm": sum(1 for l in llamadas if not l["ok"]),
            })
            print(f"  [{modo}] {conv['nombre'][:20]} t{n}: {filas[-1]['segundos']:.2f}s "
                  f"{filas[-1]['tokens_entrada']}+{filas[-1]['tokens_salida']} tok "
                  f"{len(llamadas)} llamadas -> {r['pregunta_interpretada'][:70]}")
            time.sleep(pausa)
    finally:
        historial.borrar_conversacion(cid)
    return filas


def _prom(valores):
    valores = [v for v in valores if v is not None]
    return statistics.mean(valores) if valores else 0


def informe(filas):
    L = ["# Medición: costo de la memoria conversacional", ""]
    L.append(f"Modelo: `{parametros.obtener('modelo_llm')}` (Groq). Respuesta en modo "
             f"`{MODO_RESPUESTA}` (curso {CURSO}). Ventana de memoria: "
             f"{parametros.obtener('memoria_ventana')} mensajes.")
    L.append(f"Turnos medidos: {len(filas)} "
             f"({len(CONVERSACIONES)} conversaciones × {len(CONVERSACIONES[0]['turnos'])} turnos "
             f"× {len({f['repeticion'] for f in filas})} repeticiones × 2 estrategias).")
    L.append("El tiempo excluye las esperas por límite de peticiones de Groq (se reportan aparte).")
    L.append("")
    L.append("## Promedio por turno")
    L.append("")
    L.append("| Estrategia | Llamadas al modelo | Tokens entrada | Tokens salida | Tokens totales | Tiempo (s) | Aciertos |")
    L.append("|---|---|---|---|---|---|---|")
    resumen = {}
    for modo in ("concatenacion", "resumen"):
        fs = [f for f in filas if f["modo"] == modo]
        evaluables = [f for f in fs if f["acierto"] is not None]
        aciertos = sum(1 for f in evaluables if f["acierto"])
        resumen[modo] = {
            "llamadas": _prom([f["n_llamadas"] for f in fs]),
            "entrada": _prom([f["tokens_entrada"] for f in fs]),
            "salida": _prom([f["tokens_salida"] for f in fs]),
            "segundos": _prom([f["segundos"] for f in fs]),
            "aciertos": aciertos, "evaluables": len(evaluables),
        }
        s = resumen[modo]
        L.append(f"| {modo} | {s['llamadas']:.2f} | {s['entrada']:.0f} | {s['salida']:.0f} | "
                 f"{s['entrada'] + s['salida']:.0f} | {s['segundos']:.2f} | "
                 f"{aciertos}/{len(evaluables)} ({100 * aciertos / max(1, len(evaluables)):.0f} %) |")
    a, b = resumen["concatenacion"], resumen["resumen"]
    tok_a, tok_b = a["entrada"] + a["salida"], b["entrada"] + b["salida"]
    L.append("")
    L.append(f"**Diferencia:** la estrategia con resumen usa {tok_b / max(1, tok_a):.2f}× los tokens "
             f"({tok_b - tok_a:+.0f} por turno) y {b['segundos'] / max(0.001, a['segundos']):.2f}× el tiempo "
             f"({b['segundos'] - a['segundos']:+.2f} s por turno).")
    L.append("")

    L.append("## Desglose de la estrategia con resumen (promedio por llamada)")
    L.append("")
    L.append("| Propósito | Llamadas | Tokens entrada | Tokens salida | Tiempo (s) |")
    L.append("|---|---|---|---|---|")
    todas = [l for f in filas if f["modo"] == "resumen" for l in f["llamadas"]]
    for prop in ("reescritura", "resumen", "respuesta"):
        ls = [l for l in todas if l["proposito"] == prop]
        if ls:
            L.append(f"| {prop} | {len(ls)} | {_prom([l['tokens_entrada'] for l in ls]):.0f} | "
                     f"{_prom([l['tokens_salida'] for l in ls]):.0f} | {_prom([l['segundos'] for l in ls]):.2f} |")
    L.append("")

    L.append("## Cómo se interpretó cada pregunta (repetición 1)")
    for conv in CONVERSACIONES:
        L.append("")
        L.append(f"### {conv['nombre']}")
        L.append("")
        L.append("| # | Pregunta | Concatenación | ✓ | Resumen + reescritura | ✓ |")
        L.append("|---|---|---|---|---|---|")
        for n, (pregunta, _) in enumerate(conv["turnos"], start=1):
            par = {f["modo"]: f for f in filas if f["conversacion"] == conv["nombre"]
                   and f["turno"] == n and f["repeticion"] == 1}
            def celda(m):
                f = par.get(m)
                if not f:
                    return "—", "—"
                marca = {True: "sí", False: "no", None: "—"}[f["acierto"]]
                return f["interpretada"].replace("|", "/"), marca
            c1, a1 = celda("concatenacion")
            c2, a2 = celda("resumen")
            L.append(f"| {n} | {pregunta} | {c1} | {a1} | {c2} | {a2} |")
    L.append("")
    fallos = sum(f["fallos_llm"] for f in filas)
    espera = sum(f["espera_limite"] for f in filas)
    L.append(f"Llamadas fallidas al modelo: {fallos}. Tiempo total esperando por límite "
             f"de peticiones (excluido): {espera:.1f} s.")
    L.append("")
    L.append("*Aciertos*: la respuesta contiene el dato esperado (palabra clave). Es una "
             "medida aproximada; no reemplaza la evaluación con RAGAS.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeticiones", type=int, default=1)
    ap.add_argument("--pausa", type=float, default=12, help="segundos entre turnos (cuota de Groq)")
    args = ap.parse_args()

    original = parametros.obtener("memoria_modo")
    filas = []
    try:
        for rep in range(1, args.repeticiones + 1):
            for modo in ("concatenacion", "resumen"):
                parametros.actualizar("memoria_modo", modo, "admin")
                for conv in CONVERSACIONES:
                    filas += correr_conversacion(modo, conv, rep, args.pausa)
    finally:
        parametros.actualizar("memoria_modo", original, "admin")

    with open(SALIDA + ".json", "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)
    with open(SALIDA + ".md", "w", encoding="utf-8") as f:
        f.write(informe(filas))
    print(f"\nListo: {SALIDA}.md")


if __name__ == "__main__":
    main()
