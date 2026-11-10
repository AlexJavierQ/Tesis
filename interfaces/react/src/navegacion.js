import {
  MessageSquare, FileText, BookOpen, ChartColumn, Users, SlidersHorizontal, History, Landmark,
} from "lucide-react";

/**
 * Menu lateral de cada rol, agrupado por area.
 * Cada seccion: { clave, texto, icono }. La clave decide que pantalla se ve.
 * (La API valida los mismos permisos: esto solo ordena lo que cada uno ve.)
 */
const CHAT = { clave: "chat", texto: "Chat", icono: MessageSquare };
const DOCUMENTOS = { clave: "documentos", texto: "Documentos", icono: FileText };
const CURSOS = { clave: "cursos", texto: "Cursos y docentes", icono: BookOpen };
const METRICAS = { clave: "metricas", texto: "Análisis de consultas", icono: ChartColumn };
const USUARIOS = { clave: "usuarios", texto: "Usuarios", icono: Users };
const INSTITUCION = { clave: "institucion", texto: "Facultades y carreras", icono: Landmark };
const CONFIGURACION = { clave: "configuracion", texto: "Configuración", icono: SlidersHorizontal };
const REGISTRO = { clave: "registro", texto: "Registro de actividad", icono: History };

// En la V1 el chat es solo del estudiante (la API rechaza /preguntar a los
// demas roles), asi que docente y coordinacion no lo tienen en su menu.
export const MENU = {
  estudiante: [
    { titulo: "Asistente", secciones: [CHAT] },
  ],
  docente: [
    { titulo: "Mis cursos", secciones: [DOCUMENTOS, METRICAS] },
  ],
  coordinacion: [
    { titulo: "Mis carreras", secciones: [METRICAS, DOCUMENTOS, CURSOS] },
    { titulo: "Personas", secciones: [USUARIOS] },
  ],
  administrador: [
    { titulo: "Institución", secciones: [INSTITUCION, USUARIOS] },
    { titulo: "Sistema", secciones: [CONFIGURACION, REGISTRO] },
  ],
};

export const NOMBRE_ROL = {
  estudiante: "Estudiante",
  docente: "Docente",
  coordinacion: "Coordinación",
  administrador: "Administrador",
};
