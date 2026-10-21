/**
 * Formato de datos para mostrarlos en lenguaje natural.
 */

const FORMATO_FECHA = new Intl.DateTimeFormat("es-EC", {
  day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

/** "2026-10-19 19:16:05" (como lo guarda la BD) -> "19 oct 2026, 19:16" */
export function fecha(texto) {
  if (!texto) return "";
  const d = new Date(texto.replace(" ", "T"));
  return isNaN(d) ? texto : FORMATO_FECHA.format(d);
}

/** "computacion" -> "Computacion" (nombres guardados en minusculas) */
export function nombre(texto) {
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : "";
}

/** 1 -> "1 documento", 3 -> "3 documentos" */
export function plural(n, singular, pluralTexto = singular + "s") {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}
