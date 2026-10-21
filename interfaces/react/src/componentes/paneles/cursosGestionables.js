import { api } from "../../api";

/**
 * Cursos que el usuario puede gestionar en una carrera:
 *  - coordinacion: todos los cursos de la carrera
 *  - docente: solo los que la coordinacion le asigno
 */
export async function cursosGestionables(usuario, carrera) {
  if (usuario.rol === "docente") {
    return usuario.cursos_asignados
      .filter((a) => a.carrera === carrera)
      .map((a) => a.curso);
  }
  return api.cursos(carrera);
}
