# -*- coding: utf-8 -*-
"""
PARAMETROS DEL SISTEMA (configuracion editable sin tocar el codigo).

Antes estos valores eran constantes escritas en el codigo (UMBRAL = 0.65,
TOP_K = 8...). Ahora viven en la tabla `parametros` de la BD y el
ADMINISTRADOR los cambia desde la interfaz. Cada modulo los lee en el
momento de usarlos, asi un cambio se aplica en la siguiente pregunta sin
reiniciar nada.

Cada parametro guarda su tipo y su rango permitido, para no aceptar un
valor que rompa el sistema (p. ej. un umbral de 5 o un TOP_K de 0).

OJO: la API key del LLM NO es un parametro. Es un secreto y sigue en
.streamlit/secrets.toml (o en variables de entorno), fuera de la BD.
"""
from nucleo import bd

# clave: (valor por defecto, tipo, minimo, maximo, descripcion)
DEFECTOS = {
    "umbral_similitud": ("0.65", "decimal", 0.30, 1.00,
        "Distancia máxima para aceptar un fragmento. Más bajo = más estricto "
        "(se abstiene más); más alto = responde más, con más riesgo de inventar."),
    "top_k": ("8", "entero", 1, 20,
        "Cuántos fragmentos se recuperan por ámbito en cada pregunta."),
    "max_citas": ("3", "entero", 1, 10,
        "Cuántas fuentes (archivo y página) se muestran bajo cada respuesta."),
    "modelo_llm": ("openai/gpt-oss-20b", "texto", None, None,
        "Modelo de Groq que redacta las respuestas. Permite cambiarlo si el "
        "proveedor retira el actual."),
    "temperatura": ("0.2", "decimal", 0.0, 1.0,
        "Creatividad del modelo. Más bajo = respuestas más fieles a los documentos."),
    "umbral_tema": ("0.70", "decimal", 0.40, 0.95,
        "Similitud mínima para agrupar dos preguntas como el mismo tema en las métricas."),
    "horas_sesion": ("8", "entero", 1, 72,
        "Horas que dura una sesión antes de pedir que se inicie sesión de nuevo."),
    "max_pdf_mb": ("25", "entero", 1, 100,
        "Tamaño máximo de un PDF que se puede subir."),
    "memoria_modo": ("resumen", "texto", None, None,
        "'resumen': mensajes recientes + resumen de lo anterior, y el modelo "
        "reescribe la pregunta para que se entienda sola. 'concatenacion': solo "
        "agrega la pregunta anterior si la actual parece un seguimiento (más "
        "barato, sin llamadas extra al modelo, pero entiende menos)."),
    "memoria_ventana": ("6", "entero", 2, 20,
        "Cuántos mensajes recientes se envían completos; los anteriores se resumen."),
    "mensaje_abstencion": (
        "No tengo informacion oficial sobre eso. Te recomiendo consultar con la coordinacion.",
        "texto", None, None,
        "Lo que responde el asistente cuando la respuesta no está en los documentos."),
    "mensaje_ayuda": (
        "Soy el asistente de Practicum de la UTPL. Respondo con los reglamentos y "
        "silabos oficiales. Preguntame por ejemplo: cuantas horas necesitas, cual es "
        "el plazo del informe, que formato usar, cual es la nota minima o los "
        "prerrequisitos. Si algo no esta en los documentos, te derivo a la coordinacion.",
        "texto", None, None,
        "Respuesta a saludos y a pedidos de ayuda (\"hola\", \"¿qué puedes hacer?\")."),
}

# parametros de texto que solo aceptan ciertos valores
OPCIONES = {
    "memoria_modo": ("resumen", "concatenacion"),
}

# AREAS: como se agrupan los parametros en la pantalla de Configuracion.
# (clave del area, titulo, descripcion, [(parametro, nombre legible), ...])
AREAS = [
    ("busqueda", "Búsqueda en documentos",
     "Cómo se encuentran los fragmentos que respaldan cada respuesta.",
     [("umbral_similitud", "Umbral de similitud"),
      ("top_k", "Fragmentos por búsqueda"),
      ("max_citas", "Citas por respuesta")]),
    ("modelo", "Modelo de IA",
     "Qué modelo redacta las respuestas y con cuánta libertad.",
     [("modelo_llm", "Modelo"),
      ("temperatura", "Temperatura")]),
    ("memoria", "Memoria conversacional",
     "Cómo el asistente entiende preguntas que dependen de lo conversado antes.",
     [("memoria_modo", "Estrategia de memoria"),
      ("memoria_ventana", "Mensajes recientes completos")]),
    ("mensajes", "Mensajes del asistente",
     "Textos fijos que el asistente usa en situaciones especiales.",
     [("mensaje_abstencion", "Cuando no hay información"),
      ("mensaje_ayuda", "Saludo y ayuda")]),
    ("acceso", "Sesiones y archivos",
     "Límites de uso de la plataforma.",
     [("horas_sesion", "Duración de la sesión (horas)"),
      ("max_pdf_mb", "Tamaño máximo de PDF (MB)")]),
    ("metricas", "Métricas",
     "Cómo se agrupan las consultas en el panel de métricas.",
     [("umbral_tema", "Similitud para agrupar temas")]),
]


def _sembrar():
    """
    Inserta los parametros que falten con su valor por defecto. De los que ya
    existen NO toca el valor (lo eligio el administrador); solo actualiza la
    descripcion y el rango, que son parte del codigo.
    """
    with bd.transaccion() as c:
        for clave, (valor, tipo, mn, mx, desc) in DEFECTOS.items():
            c.execute("""INSERT OR IGNORE INTO parametros
                         (clave, valor, tipo, minimo, maximo, descripcion)
                         VALUES (?,?,?,?,?,?)""", (clave, valor, tipo, mn, mx, desc))
            c.execute("UPDATE parametros SET descripcion=?, minimo=?, maximo=? WHERE clave=?",
                      (desc, mn, mx, clave))


def _convertir(valor, tipo):
    return int(valor) if tipo == "entero" else float(valor) if tipo == "decimal" else valor


def obtener(clave):
    """Valor de un parametro, ya convertido a su tipo (int, float o str)."""
    with bd.transaccion() as c:
        fila = c.execute("SELECT valor, tipo FROM parametros WHERE clave=?", (clave,)).fetchone()
    if not fila:  # por si la BD aun no lo tiene
        valor, tipo = DEFECTOS[clave][0], DEFECTOS[clave][1]
        return _convertir(valor, tipo)
    return _convertir(fila[0], fila[1])


def listar():
    """Todos los parametros con su descripcion, rango y ultima modificacion."""
    with bd.transaccion() as c:
        filas = c.execute("""
            SELECT p.clave, p.valor, p.tipo, p.minimo, p.maximo, p.descripcion,
                   p.actualizado_en, IFNULL(u.usuario, '—')
            FROM parametros p LEFT JOIN usuarios u ON p.actualizado_por = u.id
            ORDER BY p.clave""").fetchall()
    return [{"clave": f[0], "valor": f[1], "tipo": f[2], "minimo": f[3], "maximo": f[4],
             "descripcion": f[5], "actualizado_en": f[6], "actualizado_por": f[7],
             "defecto": DEFECTOS.get(f[0], ("",))[0],
             "opciones": list(OPCIONES.get(f[0], []))}
            for f in filas]


def por_areas():
    """
    Parametros agrupados por area, en el orden de AREAS, cada uno con su
    nombre legible: [{clave, titulo, descripcion, parametros: [...]}].
    """
    todos = {p["clave"]: p for p in listar()}
    salida = []
    for clave, titulo, descripcion, miembros in AREAS:
        params = []
        for nombre, etiqueta in miembros:
            if nombre in todos:
                params.append({**todos[nombre], "etiqueta": etiqueta})
        salida.append({"clave": clave, "titulo": titulo,
                       "descripcion": descripcion, "parametros": params})
    return salida


def actualizar(clave, valor, usuario):
    """
    Cambia un parametro validando su tipo y rango. ValueError si no es valido.
    Devuelve el valor anterior (para dejarlo en la bitacora).
    """
    with bd.transaccion() as c:
        fila = c.execute("SELECT valor, tipo, minimo, maximo FROM parametros WHERE clave=?",
                         (clave,)).fetchone()
        if not fila:
            raise ValueError("Parametro desconocido.")
        anterior, tipo, mn, mx = fila
        texto = str(valor).strip()
        if tipo == "texto":
            if not texto:
                raise ValueError("El valor no puede estar vacio.")
            if clave in OPCIONES and texto not in OPCIONES[clave]:
                raise ValueError(f"Debe ser uno de: {', '.join(OPCIONES[clave])}.")
        else:
            try:
                numero = _convertir(texto, tipo)
            except ValueError:
                raise ValueError(f"Debe ser un numero {tipo}.")
            if (mn is not None and numero < mn) or (mx is not None and numero > mx):
                raise ValueError(f"Debe estar entre {mn:g} y {mx:g}.")
            texto = str(numero)
        uid = c.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
        c.execute("""UPDATE parametros SET valor=?, actualizado_por=?,
                     actualizado_en=datetime('now','localtime') WHERE clave=?""",
                  (texto, uid[0] if uid else None, clave))
    return anterior


_sembrar()
