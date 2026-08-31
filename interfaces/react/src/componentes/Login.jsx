import { useState } from "react";
import { api, setToken } from "../api";

/**
 * Formulario de login.
 * Al enviar: llama a /login, guarda el token y avisa al padre con onOk(usuario).
 */
export default function Login({ onOk }) {
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError(null); setEnviando(true);
    try {
      const r = await api.login(usuario, password);
      setToken(r.token);
      onOk(r.usuario);
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pantalla-login">
      <form className="caja-login" onSubmit={enviar}>
        <h1>Asistente de Practicum</h1>
        <p className="ayuda">
          Usuarios de demo: <b>estudiante / docente / coord</b> — contrasena: <b>demo2026</b>
        </p>
        <label>Usuario
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} required autoFocus />
        </label>
        <label>Contrasena
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <div className="aviso-error">{error}</div>}
        <button type="submit" disabled={enviando}>
          {enviando ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
