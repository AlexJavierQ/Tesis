import { useState } from "react";
import { GraduationCap, CircleAlert } from "lucide-react";
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
        <div>
          <div className="marca-logo"><GraduationCap size={24} /></div>
          <h1>Asistente de Prácticum</h1>
          <p className="subtitulo">Inicia sesión con tu usuario o correo institucional.</p>
        </div>

        <label className="campo">
          <span>Usuario o correo</span>
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)}
                 autoComplete="username" required autoFocus />
        </label>
        <label className="campo">
          <span>Contraseña</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                 autoComplete="current-password" required />
        </label>

        {error && <div className="error-formulario"><CircleAlert size={16} />{error}</div>}

        <button type="submit" className="btn btn-primario" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
