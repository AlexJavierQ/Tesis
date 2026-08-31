# -*- coding: utf-8 -*-
"""
Banco de EVALUACION DEL SISTEMA sobre el corpus real.

No confundir con pruebas_herramientas.py: aquel compara herramientas entre si
(que lector de PDF, que modelo de embeddings) sobre un PDF de demostracion.
Este mide si el sistema RESPONDE BIEN sobre los reglamentos oficiales.

Metricas (equivalentes a las de recuperacion de RAGAS, calculadas sin
depender de un LLM juez, para no consumir cuota ni introducir su varianza):

  recall@k        el fragmento correcto aparece entre los k recuperados
  precision@1     el PRIMER fragmento recuperado ya es el correcto
  MRR             1/posicion del primer acierto (premia que salga arriba)
  abstencion      en preguntas fuera del corpus, ¿se abstiene como debe?
  latencia        ms de recuperacion y de respuesta completa

Uso:
  python evaluacion.py                  evalua con preguntas_eval.json
  python evaluacion.py --sin-llm        solo recuperacion (no gasta cuota)
  python evaluacion.py --salida x.md    escribe el informe en markdown
"""
import argparse
import json
import os
import statistics
import sys
import time

# permite ejecutar este archivo directamente: agrega la raiz del proyecto al path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import config  # noqa: F401  (carga las keys antes que el motor)
from nucleo import rag

BASE = os.path.dirname(__file__)
PREGUNTAS = os.path.join(BASE, "preguntas_eval.json")


def cargar_preguntas(ruta):
    if not os.path.exists(ruta):
        raise SystemExit(
            f"No encuentro {ruta}.\n"
            "Crea el banco de preguntas primero (ver preguntas_eval.ejemplo.json)."
        )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _acierta(hit, caso):
    """
    ¿Este fragmento recuperado es el correcto?
    Criterio: contiene el texto esperado (normalizado) Y, si se especifico
    fuente, viene del documento correcto.
    """
    esperado = caso["contiene"].lower().strip()
    if esperado not in " ".join(hit["texto"].split()).lower():
        return False
    if caso.get("fuente") and caso["fuente"].lower() not in hit["fuente"].lower():
        return False
    return True


def evaluar(casos, con_llm=True):
    resultados = []
    from nucleo import vectorstore
    for caso in casos:
        carrera = caso.get("carrera", "computacion")
        curso = caso.get("curso")
        scopes = rag.scopes_de(carrera, curso)

        t0 = time.perf_counter()
        hits_raw = vectorstore.buscar(caso["pregunta"], k=rag.TOP_K,
                                       filtro={"scope": {"$in": scopes}})
        # normalizamos al formato que espera _acierta: {texto, fuente, ...}
        hits = [{"texto": h["texto"], "fuente": h["meta"].get("fuente", "?"),
                 "distancia": h["distancia"]} for h in hits_raw]
        ms_recuperacion = (time.perf_counter() - t0) * 1000

        fuera_de_corpus = caso.get("fuera_de_corpus", False)
        posicion = next((i + 1 for i, h in enumerate(hits) if _acierta(h, caso)), None) \
            if not fuera_de_corpus else None

        fila = {
            "pregunta": caso["pregunta"],
            "fuera_de_corpus": fuera_de_corpus,
            "cercania": caso.get("cercania", "—"),
            "posicion": posicion,
            "recall": posicion is not None,
            "top1": posicion == 1,
            "mrr": (1 / posicion) if posicion else 0.0,
            "ms_recuperacion": ms_recuperacion,
            "distancia_min": min((h["distancia"] for h in hits), default=None),
        }

        if con_llm:
            carrera = caso.get("carrera", "computacion")
            curso = caso.get("curso")
            t0 = time.perf_counter()
            r = rag.responder(caso["pregunta"], carrera, curso)
            fila["ms_total"] = (time.perf_counter() - t0) * 1000
            fila["con_respaldo"] = r["con_respaldo"]
            fila["respuesta"] = r["respuesta"]
            fila["citas"] = [f"{c['fuente']} p.{c['pagina']}" for c in r["citas"]]
            # en preguntas fuera del corpus, el acierto ES abstenerse
            fila["correcto"] = (not r["con_respaldo"]) if fuera_de_corpus else r["con_respaldo"]

        resultados.append(fila)
    return resultados


def informe(resultados, con_llm=True):
    dentro = [r for r in resultados if not r["fuera_de_corpus"]]
    fuera = [r for r in resultados if r["fuera_de_corpus"]]
    L = []
    pct = lambda xs: (100 * sum(xs) / len(xs)) if xs else 0.0   # noqa: E731

    L.append("# Evaluación del sistema sobre el corpus real\n")
    L.append(f"Preguntas evaluadas: **{len(resultados)}** "
             f"({len(dentro)} dentro del corpus, {len(fuera)} fuera).\n")

    L.append("## Recuperación\n")
    L.append("| Métrica | Valor |")
    L.append("|---|---|")
    L.append(f"| recall@{rag.TOP_K} | {pct([r['recall'] for r in dentro]):.1f} % |")
    L.append(f"| precision@1 | {pct([r['top1'] for r in dentro]):.1f} % |")
    L.append(f"| MRR | {statistics.mean([r['mrr'] for r in dentro]) if dentro else 0:.3f} |")
    lat = [r["ms_recuperacion"] for r in resultados]
    L.append(f"| Latencia de recuperación (mediana) | {statistics.median(lat):.1f} ms |")

    if con_llm:
        tot = [r["ms_total"] for r in resultados if "ms_total" in r]
        L.append(f"| Latencia total (mediana) | {statistics.median(tot) / 1000:.2f} s |")
        L.append(f"| Latencia total (máxima) | {max(tot) / 1000:.2f} s |")
        L.append(f"| Cumple RNF3 (< 8 s) | {'sí' if max(tot) < 8000 else 'NO'} |")
        L.append("\n## Comportamiento de respuesta\n")
        L.append("| Métrica | Valor |")
        L.append("|---|---|")
        L.append(f"| Responde con respaldo (dentro del corpus) | "
                 f"{pct([r['con_respaldo'] for r in dentro]):.1f} % |")
        if fuera:
            L.append(f"| Se abstiene correctamente (fuera del corpus) | "
                     f"{pct([not r['con_respaldo'] for r in fuera]):.1f} % |")

            L.append("\n### Abstención por cercanía al dominio\n")
            L.append("Cuanto más se parece la pregunta al dominio, más difícil es "
                     "distinguirla por similitud.\n")
            L.append("| Cercanía | n | Se abstiene | Distancia mín. (mediana) |")
            L.append("|---|---|---|---|")
            for banda in ("lejana", "media", "cercana"):
                grupo = [r for r in fuera if r["cercania"] == banda]
                if not grupo:
                    continue
                dmed = statistics.median([r["distancia_min"] for r in grupo
                                          if r["distancia_min"] is not None])
                L.append(f"| {banda} | {len(grupo)} | "
                         f"{pct([not r['con_respaldo'] for r in grupo]):.0f} % | {dmed:.3f} |")

    L.append("\n## Detalle por pregunta\n")
    cab = "| # | Pregunta | Esperado | Pos. | dist. mín."
    sep = "|---|---|---|---|---|"
    if con_llm:
        cab += " | Respaldo | Correcto"
        sep += "---|---|"
    L.append(cab + " |")
    L.append(sep)
    for i, r in enumerate(resultados, 1):
        esperado = "abstenerse" if r["fuera_de_corpus"] else "responder"
        pos = r["posicion"] if r["posicion"] else "—"
        dist = f"{r['distancia_min']:.3f}" if r["distancia_min"] is not None else "—"
        fila = f"| {i} | {r['pregunta'][:58]} | {esperado} | {pos} | {dist}"
        if con_llm:
            fila += f" | {'si' if r['con_respaldo'] else 'no'}"
            fila += f" | {'OK' if r['correcto'] else '**FALLA**'}"
        L.append(fila + " |")

    fallos = [r for r in resultados if (r.get("correcto") is False)
              or (not r["fuera_de_corpus"] and not r["recall"])]
    if fallos:
        L.append(f"\n## Fallos a revisar ({len(fallos)})\n")
        for r in fallos:
            motivo = ("no recuperó el fragmento correcto" if not r["recall"]
                      and not r["fuera_de_corpus"] else
                      "debía abstenerse y respondió" if r["fuera_de_corpus"]
                      else "no respondió teniendo el fragmento")
            L.append(f"- **{r['pregunta']}** — {motivo} "
                     f"(distancia mínima {r['distancia_min']:.3f})"
                     if r["distancia_min"] is not None else
                     f"- **{r['pregunta']}** — {motivo}")

    L.append("\n---\n")
    from nucleo import llm as _llm
    L.append(f"Parámetros: top-k = {rag.TOP_K}, umbral de distancia = {rag.UMBRAL}, "
             f"modelo = `{_llm.MODELO}` (groq).")
    L.append("\nReproducible con `python evaluacion.py`.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preguntas", default=PREGUNTAS)
    ap.add_argument("--sin-llm", action="store_true",
                    help="solo mide recuperación (no consume cuota del LLM)")
    ap.add_argument("--salida", help="ruta del informe markdown a escribir")
    args = ap.parse_args()

    casos = cargar_preguntas(args.preguntas)
    print(f"Evaluando {len(casos)} preguntas...")
    resultados = evaluar(casos, con_llm=not args.sin_llm)
    texto = informe(resultados, con_llm=not args.sin_llm)
    # se escribe ANTES de imprimir: la consola de Windows (cp1252) no admite
    # todos los caracteres y no queremos perder el informe por eso
    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
    # errors="replace" para que un caracter no representable no aborte la corrida
    print("\n" + texto.encode(sys.stdout.encoding or "utf-8", errors="replace")
          .decode(sys.stdout.encoding or "utf-8", errors="replace"))
    if args.salida:
        print(f"\nInforme escrito en {args.salida}")


if __name__ == "__main__":
    main()
