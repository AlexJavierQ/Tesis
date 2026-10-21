import {
  MessageSquare, FileText, Building2, ChartColumn, Users, SlidersHorizontal, History,
} from "lucide-react";

/**
 * Menu lateral de cada rol, agrupado por area.
 * Cada seccion: { clave, texto, icono }. La clave decide que pantalla se ve.
 * (La API valida los mismos permisos: esto solo ordena lo que cada uno ve.)
 */
const CHAT = { clave: "chat", texto: "Chat", icono: MessageSquare };
const DOCUMENTOS = { clave: "documentos", texto: "Documentos", icono: FileText };
const ESTRUCTURA = { clave: "estructura", texto: "Estructura académica", icono: Building2 };
const METRICAS = { clave: "metricas", texto: "Métricas", icono: ChartColumn };
const USUARIOS = { clave: "usuarios", texto: "Usuarios", icono: Users };
const CONFIGURACION = { clave: "configuracion", texto: "Configuración", icono: SlidersHorizontal };
const REGISTRO = { clave: "registro", texto: "Registro de actividad", icono: History };

export const MENU = {
  estudiante: [
    { titulo: "Asistente", secciones: [CHAT] },
  ],
  docente: [
    { titulo: "Asistente", secciones: [CHAT] },
    { titulo: "Mis cursos", secciones: [DOCUMENTOS, METRICAS] },
  ],
  coordinacion: [
    { titulo: "Asistente", secciones: [CHAT] },
    { titulo: "Gestión académica", secciones: [DOCUMENTOS, ESTRUCTURA, METRICAS] },
    { titulo: "Personas", secciones: [USUARIOS] },
  ],
  administrador: [
    { titulo: "Sistema", secciones: [CONFIGURACION, REGISTRO] },
    { titulo: "Personas", secciones: [USUARIOS] },
  ],
};

export const NOMBRE_ROL = {
  estudiante: "Estudiante",
  docente: "Docente",
  coordinacion: "Coordinación",
  administrador: "Administrador",
};
