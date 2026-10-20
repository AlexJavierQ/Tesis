import { useState } from "react";
import Documentos from "./paneles/Documentos";
import Estructura from "./paneles/Estructura";
import Metricas from "./paneles/Metricas";
import Usuarios from "./paneles/Usuarios";
import Configuracion from "./paneles/Configuracion";
import Registro from "./paneles/Registro";

/**
 * Panel de gestion. Cada rol ve SOLO las pestanas que le corresponden:
 *   administrador -> Configuracion del sistema, Usuarios, Registro (bitacora)
 *   coordinacion  -> Documentos, Estructura (facultades/carreras/cursos/docentes),
 *                    Metricas, Usuarios (estudiantes y docentes)
 *   docente       -> Documentos y Metricas de SUS cursos asignados
 * Cada pestana es un componente aparte en componentes/paneles/.
 * (La API valida los mismos permisos: ocultar una pestana es solo comodidad.)
 */
const PESTANAS = {
  administrador: [
    ["configuracion", "⚙️ Configuración"],
    ["usuarios", "👥 Usuarios"],
    ["registro", "🕑 Registro"],
  ],
  coordinacion: [
    ["documentos", "📄 Documentos"],
    ["estructura", "🏛️ Estructura"],
    ["metricas", "📊 Métricas"],
    ["usuarios", "👥 Usuarios"],
  ],
  docente: [
    ["documentos", "📄 Documentos"],
    ["metricas", "📊 Métricas"],
  ],
};

export default function Admin({ usuario, carrera, refrescarUsuario }) {
  const pestanas = PESTANAS[usuario.rol] || [];
  const [pestana, setPestana] = useState(pestanas[0]?.[0]);
  const [aviso, setAviso] = useState(null);
  const [error, setError] = useState(null);

  function cambiar(p) {
    setPestana(p);
    setAviso(null);
    setError(null);
  }

  // lo que reciben todas las pestanas
  const comun = {
    usuario,
    carrera,
    refrescarUsuario,
    avisar: (m) => { setError(null); setAviso(m); },
    fallar: (m) => { setAviso(null); setError(m); },
  };

  return (
    <div className="admin">
      <nav className="admin-tabs">
        {pestanas.map(([clave, titulo]) => (
          <button key={clave} className={pestana === clave ? "activo" : ""}
                  onClick={() => cambiar(clave)}>{titulo}</button>
        ))}
      </nav>

      {aviso && <div className="aviso-ok">{aviso}</div>}
      {error && <div className="aviso-error">{error}</div>}

      {pestana === "documentos" && <Documentos {...comun} />}
      {pestana === "estructura" && <Estructura {...comun} />}
      {pestana === "metricas" && <Metricas {...comun} />}
      {pestana === "usuarios" && <Usuarios {...comun} />}
      {pestana === "configuracion" && <Configuracion {...comun} />}
      {pestana === "registro" && <Registro {...comun} />}
    </div>
  );
}
