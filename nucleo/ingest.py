# -*- coding: utf-8 -*-
"""
INGESTA de documentos: del PDF a la base vectorial.

FRAGMENTACION POR SECCIONES ("indexar chico, responder con la seccion")
  1. El PDF se divide en SECCIONES (titulo + contenido) con pdfreader.secciones.
  2. Cada seccion larga se parte en PARTES de hasta MAX_CONTEXTO caracteres,
     respetando parrafos. Una parte es lo que el modelo de lenguaje leera.
  3. Cada parte se trocea en FRAGMENTOS de TAMANO caracteres (con SOLAPE),
     precedidos por el titulo de la seccion. Esos fragmentos son los que se
     convierten en vectores: el modelo de embeddings solo lee ~128 tokens
     (~680 caracteres), asi que un trozo mas largo perderia su final.
  Al buscar, se recupera el fragmento mas parecido, pero al modelo de lenguaje
  se le entrega la PARTE completa de la seccion (metadato "contexto").

TRAZABILIDAD: cada fragmento guarda el id del documento y el numero de version
de la que sale, asi una cita apunta siempre a la version exacta usada.

CONSISTENCIA entre archivos, SQLite y ChromaDB (no hay una transaccion comun):
  - el PDF se procesa ANTES de tocar nada: si no tiene texto, se rechaza;
  - los pasos sobre archivos y BD se deshacen si algo falla a mitad;
  - reconciliar() compara catalogo y vectores y corrige diferencias; se
    ejecuta al arrancar y en la verificacion.

Estructura de carpetas:
  datos/docs/<carrera>/global/*.pdf          -> normativa de la carrera
  datos/docs/<carrera>/cursos/<curso>/*.pdf  -> documentos de un curso
  .../_versiones/*.pdf                        -> versiones anteriores (no se indexan)
"""
import os
import glob
import json
import uuid

from nucleo import pdfreader, vectorstore, bd
from nucleo.rag import DOCS

TAMANO = 500         # caracteres por fragmento indexado
SOLAPE = 80          # caracteres compartidos entre fragmentos vecinos
MAX_CONTEXTO = 1800  # tope de la parte de seccion que se entrega al modelo
MIN_TEXTO = 200      # un PDF con menos texto util se rechaza (escaneado o vacio)


def _scope(carrera, curso):
    return f"{carrera}|curso:{curso}" if curso else f"{carrera}|global"


def _carpeta(carrera, curso):
    return (os.path.join(DOCS, carrera, "cursos", curso) if curso
            else os.path.join(DOCS, carrera, "global"))


def _rel(path):
    """Ruta relativa a datos/docs/ (portable entre computadoras)."""
    return os.path.relpath(os.path.abspath(path), DOCS).replace("\\", "/")


# ---------- fragmentacion ----------
def trocear(texto):
    """Parte un texto en trozos de ~TAMANO caracteres con SOLAPE entre trozos."""
    texto = " ".join(texto.split())
    trozos, i = [], 0
    while i < len(texto):
        trozos.append(texto[i:i + TAMANO])
        i += TAMANO - SOLAPE
    return [t for t in trozos if t.strip()]


def _partes(seccion):
    """Divide una seccion en partes de hasta MAX_CONTEXTO caracteres, sin cortar parrafos."""
    partes, actual, pagina = [], [], None
    for pag, parrafo in seccion["parrafos"]:
        if actual and sum(len(p) for p in actual) + len(parrafo) > MAX_CONTEXTO:
            partes.append((pagina, "\n".join(actual)))
            actual = []
        if not actual:
            pagina = pag
        actual.append(parrafo)
    if actual:
        partes.append((pagina, "\n".join(actual)))
    return partes


def _con_grupos(secciones):
    """
    Agrupa una seccion principal numerada con sus subsecciones ("14", "14.1",
    "14.2"...). Si el grupo completo cabe en MAX_CONTEXTO, todas sus partes
    comparten como contexto el grupo entero: las subsecciones muy cortas
    (p. ej. tres listas de evidencias) se entienden mejor juntas, y encontrar
    cualquiera de ellas le entrega al modelo la seccion completa.
    Devuelve [(seccion, contexto del grupo o None)].
    """
    grupos = []
    for sec in secciones:
        numero = pdfreader._numero(sec["titulo"])
        clave = numero.split(".")[0] if numero else None
        if clave and grupos and grupos[-1][0] == clave:
            grupos[-1][1].append(sec)
        else:
            grupos.append((clave, [sec]))
    salida = []
    for clave, miembros in grupos:
        texto = "\n".join(s["titulo"] + "\n" + "\n".join(t for _, t in s["parrafos"]) for s in miembros)
        compartido = texto if clave and len(miembros) > 1 and len(texto) <= MAX_CONTEXTO else None
        salida.extend((s, compartido) for s in miembros)
    return salida


def fragmentar(path):
    """
    Lista de fragmentos de un PDF: [{texto, contexto, pagina, seccion}].
      texto    -> lo que se convierte en vector (titulo + trozo corto)
      contexto -> la parte de la seccion que leera el modelo de lenguaje
    """
    salida = []
    for sec, contexto_grupo in _con_grupos(pdfreader.secciones(path)):
        titulo = sec.get("ruta") or sec["titulo"]   # "14 Evidencias › 14.2 ..." si es subseccion
        for pagina, cuerpo in _partes(sec):
            contexto = contexto_grupo or (f"{titulo}\n{cuerpo}" if titulo else cuerpo)
            for trozo in trocear(cuerpo):
                salida.append({
                    "texto": f"{titulo}: {trozo}" if titulo else trozo,
                    "contexto": contexto,
                    "pagina": pagina,
                    "seccion": titulo,
                })
    return salida


def _validar(path):
    """Fragmenta un PDF y verifica que tenga texto suficiente. ValueError si no sirve."""
    try:
        fragmentos = fragmentar(path)
    except Exception:
        raise ValueError("No se pudo leer el PDF (archivo dañado o protegido).")
    if sum(len(f["texto"]) for f in fragmentos) < MIN_TEXTO:
        raise ValueError("El PDF casi no tiene texto seleccionable (¿es un escaneo?). "
                         "Sube una versión con texto.")
    return fragmentos


# ---------- base vectorial ----------
def _indexar(doc_id, version, nombre, scope, ruta, fragmentos):
    """Reemplaza en ChromaDB los vectores de un documento por los de esta version."""
    vectorstore.borrar({"documento_id": doc_id})
    if not fragmentos:
        return 0
    vectorstore.agregar(
        [f["texto"] for f in fragmentos],
        [{"fuente": nombre, "pagina": f["pagina"], "seccion": f["seccion"], "scope": scope,
          "path": ruta, "documento_id": doc_id, "version": version, "contexto": f["contexto"]}
         for f in fragmentos],
        [f"d{doc_id}v{version}-{i}" for i in range(len(fragmentos))],
    )
    return len(fragmentos)


def _indexar_vigente(d):
    """Indexa la version vigente de un documento del catalogo (dict de bd)."""
    fragmentos = fragmentar(os.path.join(DOCS, d["ruta"]))
    n = _indexar(d["id"], d["version"], d["nombre"], _scope(d["carrera"], d["curso"]),
                 d["ruta"], fragmentos)
    bd.actualizar_fragmentos(d["id"], d["version"], n)
    return n


# ---------- operaciones sobre documentos ----------
def guardar_documento(carrera, curso, nombre, contenido, usuario=None, restaurada_de=None):
    """
    Guarda un PDF subido como NUEVA VERSION de su documento.
      - Primero se valida el PDF en un archivo temporal (si no sirve, no se toca nada).
      - Si ya habia un archivo con ese nombre, se archiva en _versiones/.
      - Si un paso falla, se deshacen los anteriores (archivos y registro en BD).
      - Si el documento estaba DESACTIVADO, la version se guarda pero no se indexa.
    Devuelve {version, fragmentos, activo}.
    """
    carpeta = _carpeta(carrera, curso)
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, nombre)
    temporal = os.path.join(carpeta, f"_subida_{uuid.uuid4().hex}.pdf")
    with open(temporal, "wb") as f:
        f.write(contenido)
    try:
        fragmentos = _validar(temporal)
    except ValueError:
        os.remove(temporal)
        raise

    previo = bd.documento(carrera, curso, nombre)
    archivado = None          # (ruta del archivo archivado, ruta anterior) para deshacer
    registrado = None         # (doc_id, version) para deshacer
    try:
        if previo and os.path.exists(destino):
            archivo = os.path.join(carpeta, "_versiones",
                                   f"{os.path.splitext(nombre)[0]}_v{previo['version']}.pdf")
            os.makedirs(os.path.dirname(archivo), exist_ok=True)
            os.replace(destino, archivo)
            archivado = (archivo, previo["ruta"])
            bd.mover_version(previo["ruta"], _rel(archivo))
        os.replace(temporal, destino)
        registrado = bd.registrar_version(carrera, curso, nombre, _rel(destino),
                                          len(fragmentos), usuario, restaurada_de)
    except Exception:
        # deshacer en orden inverso: registro, archivo nuevo, archivo anterior
        if registrado:
            bd.quitar_version(*registrado)
        if os.path.exists(temporal):
            os.remove(temporal)
        elif archivado or not previo:
            if os.path.exists(destino):
                os.remove(destino)
        if archivado:
            os.replace(archivado[0], destino)
            bd.mover_version(_rel(archivado[0]), archivado[1])
        raise

    doc_id, version = registrado
    activo = previo["activo"] if previo else True
    if activo:
        # si esto falla, la version queda registrada y reconciliar() la indexa al arrancar
        _indexar(doc_id, version, nombre, _scope(carrera, curso), _rel(destino), fragmentos)
    else:
        vectorstore.borrar({"documento_id": doc_id})
    return {"version": version, "fragmentos": len(fragmentos), "activo": activo}


def restaurar_version(doc_id, numero, usuario=None):
    """
    Vuelve a una version anterior AL ESTILO GIT (revert): no borra ni reescribe
    nada; copia el contenido de la version `numero` como una version NUEVA.
      v1, v2, v3 (vigente)  --restaurar v1-->  v1, v2, v3, v4 (= copia de v1)
    """
    d = bd.documento_por_id(doc_id)
    if not d:
        raise ValueError("Documento no encontrado.")
    elegida = next((v for v in bd.versiones_de(doc_id) if v["numero"] == numero), None)
    if not elegida:
        raise ValueError("Esa version no existe.")
    if numero == d["version"]:
        raise ValueError("Esa ya es la version vigente.")
    with open(os.path.join(DOCS, elegida["ruta"]), "rb") as f:
        contenido = f.read()
    return guardar_documento(d["carrera"], d["curso"], d["nombre"], contenido, usuario,
                             restaurada_de=numero)


def cambiar_estado(doc_id, activo):
    """
    Activa o desactiva un documento.
      desactivar -> se quitan sus vectores (el chat deja de usarlo)
      activar    -> se vuelve a indexar su version vigente
    """
    d = bd.documento_por_id(doc_id)
    if not d:
        raise ValueError("Documento no encontrado.")
    bd.cambiar_estado_documento(doc_id, activo)
    if activo:
        _indexar_vigente({**d, "activo": True})
    else:
        vectorstore.borrar({"documento_id": doc_id})


def borrar_documento(doc_id):
    """Elimina un documento: sus vectores, su registro y sus archivos (todas las versiones)."""
    d = bd.documento_por_id(doc_id)
    if not d:
        raise ValueError("Documento no encontrado.")
    vectorstore.borrar({"documento_id": doc_id})
    for ruta in bd.borrar_documento(doc_id):
        archivo = os.path.join(DOCS, ruta)
        if os.path.exists(archivo):
            os.remove(archivo)
    return d


# ---------- coherencia entre catalogo, archivos y vectores ----------
def reconciliar():
    """
    Revisa que ChromaDB refleje exactamente el catalogo de la BD y corrige:
      - documento activo sin vectores, o con vectores de otra version -> se reindexa
      - documento desactivado con vectores                              -> se borran
      - vectores de documentos que ya no existen (o de formato antiguo)  -> se borran
    Devuelve un informe {reindexados, limpiados, huerfanos, archivos_faltantes}.
    """
    informe = {"reindexados": [], "limpiados": [], "huerfanos": 0, "archivos_faltantes": []}
    vectores = vectorstore.metadatos()
    por_doc = {}
    for vid, meta in vectores.items():
        por_doc.setdefault(meta.get("documento_id"), []).append((vid, meta))

    catalogo = {d["id"]: d for d in bd.todos_los_documentos()}
    for doc_id, d in catalogo.items():
        suyos = por_doc.get(doc_id, [])
        if not d["activo"]:
            if suyos:
                vectorstore.borrar_ids([vid for vid, _ in suyos])
                informe["limpiados"].append(d["nombre"])
            continue
        if not os.path.exists(os.path.join(DOCS, d["ruta"])):
            informe["archivos_faltantes"].append(d["ruta"])
            continue
        al_dia = suyos and all(m.get("version") == d["version"] for _, m in suyos) \
            and len(suyos) == d["fragmentos"]
        if not al_dia:
            _indexar_vigente(d)
            informe["reindexados"].append(d["nombre"])

    huerfanos = [vid for doc_id, lista in por_doc.items() if doc_id not in catalogo
                 for vid, _ in lista]
    vectorstore.borrar_ids(huerfanos)
    informe["huerfanos"] = len(huerfanos)
    return informe


def indexar_todo():
    """
    Registra en el catalogo los PDF de datos/docs/ que aun no estan (p. ej. al
    instalar en otra computadora) y deja la base vectorial al dia.
    """
    if not os.path.isdir(DOCS):
        print(f"No existe la carpeta {DOCS}")
        return
    # vigencias del corpus versionadas junto a los PDF (la BD no viaja en git)
    ruta_vigencias = os.path.join(DOCS, "vigencias.json")
    vigencias = {}
    if os.path.exists(ruta_vigencias):
        with open(ruta_vigencias, encoding="utf-8") as f:
            vigencias = json.load(f)
    for carrera in sorted(os.listdir(DOCS)):
        if not os.path.isdir(os.path.join(DOCS, carrera)):
            continue
        ambitos = [(None, os.path.join(DOCS, carrera, "global"))]
        cursos_dir = os.path.join(DOCS, carrera, "cursos")
        if os.path.isdir(cursos_dir):
            ambitos += [(c, os.path.join(cursos_dir, c)) for c in sorted(os.listdir(cursos_dir))
                        if os.path.isdir(os.path.join(cursos_dir, c))]
        for curso, carpeta in ambitos:
            for p in glob.glob(os.path.join(carpeta, "*.pdf")):
                nombre = os.path.basename(p)
                if nombre.startswith("_") or bd.documento(carrera, curso, nombre):
                    continue
                try:
                    fragmentos = _validar(p)
                except ValueError as e:
                    print(f"  [omitido] {nombre}: {e}")
                    continue
                doc_id, _ = bd.registrar_version(carrera, curso, nombre, _rel(p), len(fragmentos))
                if vigencias.get(_rel(p)):
                    bd.cambiar_vigencia(doc_id, vigencias[_rel(p)])
                print(f"  [registrado] {_scope(carrera, curso)} {nombre}")
    informe = reconciliar()
    print(f"  reindexados: {informe['reindexados'] or 'ninguno'} | "
          f"vectores huerfanos borrados: {informe['huerfanos']}")
    if informe["archivos_faltantes"]:
        print(f"  ATENCION, faltan archivos: {informe['archivos_faltantes']}")
    print(f"\nListo. {vectorstore.contar()} fragmentos indexados en total.")


if __name__ == "__main__":
    indexar_todo()
