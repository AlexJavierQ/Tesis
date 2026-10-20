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
        "Distancia maxima para aceptar un fragmento. Mas bajo = mas estricto "
        "(se abstiene mas); mas alto = responde mas, con mas riesgo de alucinar."),
    "top_k": ("8", "entero", 1, 20,
        "Cuantos fragmentos se recuperan por ambito en cada pregunta."),
    "max_citas": ("3", "entero", 1, 10,
        "Cuantas fuentes (archivo y pagina) se muestran bajo cada respuesta."),
    "modelo_llm": ("openai/gpt-oss-20b", "texto", None, None,
        "Modelo de Groq que redacta las respuestas. Permite cambiarlo si el "
        "proveedor retira el actual."),
    "temperatura": ("0.2", "decimal", 0.0, 1.0,
        "Creatividad del modelo. Bajo = respuestas mas fieles al contexto."),
    "umbral_tema": ("0.70", "decimal", 0.40, 0.95,
        "Similitud minima para agrupar dos preguntas como el mismo tema en las metricas."),
    "horas_sesion": ("8", "entero", 1, 72,
        "Horas que dura una sesion antes de pedir login de nuevo."),
    "max_pdf_mb": ("25", "entero", 1, 100,
        "Tamano maximo de un PDF que se puede subir."),
    "mensaje_abstencion": (
        "No tengo informacion oficial sobre eso. Te recomiendo consultar con la coordinacion.",
        "texto", None, None,
        "Lo que responde el asistente cuando la respuesta no esta en los documentos."),
    "mensaje_ayuda": (
        "Soy el asistente de Practicum de la UTPL. Respondo con los reglamentos y "
        "silabos oficiales. Preguntame por ejemplo: cuantas horas necesitas, cual es "
        "el plazo del informe, que formato usar, cual es la nota minima o los "
        "prerrequisitos. Si algo no esta en los documentos, te derivo a la coordinacion.",
        "texto", None, None,
        "Respuesta a saludos y a pedidos de ayuda (\"hola\", \"que puedes hacer\")."),
}


def _sembrar():
    """Inserta los parametros que falten con su valor por defecto (no pisa los existentes)."""
    with bd.transaccion() as c:
        for clave, (valor, tipo, mn, mx, desc) in DEFECTOS.items():
            c.execute("""INSERT OR IGNORE INTO parametros
                         (clave, valor, tipo, minimo, maximo, descripcion)
                         VALUES (?,?,?,?,?,?)""", (clave, valor, tipo, mn, mx, desc))


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
             "defecto": DEFECTOS.get(f[0], ("",))[0]}
            for f in filas]


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
