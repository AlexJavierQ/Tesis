import { useEffect, useState } from "react";
import { api } from "../api";

export default function Metricas({ carrera, curso }) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setDatos(null); setError(null);
    api.metricas(carrera, curso).then(setDatos).catch((e) => setError(e.message));
  }, [carrera, curso]);

  if (error) return <div className="aviso-error">No pude cargar las métricas: {error}</div>;
  if (!datos) return <p className="vacio">Cargando métricas…</p>;
  if (datos.total === 0)
    return <p className="vacio">Todavía no hay consultas registradas en este ámbito.</p>;

  const maximo = Math.max(...datos.temas.map((t) => t.n), 1);

  return (
    <div className="met-panel">
      <div className="met-tarjetas">
        <div className="met-tarjeta">
          <span className="met-num">{datos.total}</span>
          <span className="met-lbl">consultas</span>
        </div>
        <div className="met-tarjeta">
          <span className="met-num">{datos.pct_respaldo}%</span>
          <span className="met-lbl">resueltas con documentos</span>
        </div>
        <div className="met-tarjeta">
          <span className="met-num">{datos.sin_respaldo.length}</span>
          <span className="met-lbl">vacíos por cubrir</span>
        </div>
      </div>

      <h4>Lo que más preguntan</h4>
      <p className="met-sub">Agrupado por significado, no por texto exacto.</p>
      <ul className="met-barras">
        {datos.temas.map((t) => (
          <li key={t.tema}>
            <span className="barra-lbl" title={t.tema}>{t.tema}</span>
            <span className="barra-via">
              <span className="barra-fill" style={{ width: `${(t.n / maximo) * 100}%` }} />
            </span>
            <span className="barra-n">{t.n}</span>
          </li>
        ))}
      </ul>

      {datos.sin_respaldo.length > 0 && (
        <>
          <h4>Preguntas que no supo responder</h4>
          <p className="met-sub">Pistas de qué documentos faltan en el corpus.</p>
          <ul className="met-huecos">
            {datos.sin_respaldo.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}
