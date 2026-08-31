# -*- coding: utf-8 -*-
"""
Verifica si un PDF es apto para el asistente ANTES de subirlo.

Reglas (ver documentacion/FORMATO_DOCUMENTOS.md):
  - Debe ser PDF con texto seleccionable (no escaneado).
  - Pesa menos de 20 MB.
  - Al menos el 70% de las paginas deben tener texto util.

Uso:  python revisar_pdf.py <ruta.pdf>
"""
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Falta PyMuPDF. Instala con:  pip install pymupdf")
    sys.exit(2)

MIN_CARACTERES_UTILES = 100    # menos que esto = pagina 'vacia' o solo imagen
LIMITE_MB = 20
PCT_PAGINAS_CON_TEXTO_MIN = 70


def revisar(path):
    print(f"\n=== Revision de {os.path.basename(path)} ===")

    if not os.path.exists(path):
        # Windows a veces pasa argv con encoding raro; intenta con glob
        import glob
        candidatos = glob.glob(path)
        if candidatos:
            path = candidatos[0]
        else:
            print(f"[!] El archivo no existe: {path}")
            return False

    if not path.lower().endswith(".pdf"):
        print("[!] No es un archivo .pdf")
        return False

    tam_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"    Tamano: {tam_mb:.2f} MB")
    if tam_mb > LIMITE_MB:
        print(f"[!] Excede el limite de {LIMITE_MB} MB. No apto.")
        return False

    try:
        doc = fitz.open(path)
    except Exception as e:
        print(f"[!] No se puede abrir el PDF: {e}")
        return False

    total = doc.page_count
    con_texto = 0
    solo_imagen = []
    detalle = []

    for i in range(total):
        texto = doc[i].get_text().strip()
        # descarta paginas con solo pie de pagina generico
        limpio = " ".join(texto.split())
        n = len(limpio)
        if n >= MIN_CARACTERES_UTILES:
            con_texto += 1
            detalle.append((i + 1, n, "OK"))
        else:
            solo_imagen.append(i + 1)
            detalle.append((i + 1, n, "poca info (posible imagen)"))

    pct = 100 * con_texto / total if total else 0

    print(f"    Paginas totales: {total}")
    print(f"    Paginas con texto util: {con_texto} ({pct:.0f}%)")
    if solo_imagen:
        print(f"    Paginas sin texto util: {solo_imagen}")

    print("\n    Detalle por pagina (max 30):")
    for pag, chars, estado in detalle[:30]:
        print(f"      pag. {pag:3d}  {chars:5d} caracteres  {estado}")
    if len(detalle) > 30:
        print(f"      ... ({len(detalle) - 30} paginas mas)")

    print()
    if pct < PCT_PAGINAS_CON_TEXTO_MIN:
        print(f"[X] NO APTO. Menos del {PCT_PAGINAS_CON_TEXTO_MIN}% de las paginas")
        print("    tienen texto util. El PDF probablemente esta escaneado")
        print("    o contiene muchos diagramas sin texto acompanante.")
        print("    Revisa la seccion 4 de FORMATO_DOCUMENTOS.md.")
        return False

    print("[OK] PDF APTO para subir al sistema.")
    if solo_imagen:
        print(f"    (Aviso: {len(solo_imagen)} paginas tienen poca info.")
        print(f"     Considera anadir texto descriptivo a los diagramas.)")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ok = revisar(sys.argv[1])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
