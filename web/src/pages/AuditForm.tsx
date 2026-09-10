import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAudit } from "../api";

export default function AuditForm() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { id } = await createAudit(url);
      navigate(`/auditoria/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido.");
      setLoading(false);
    }
  }

  return (
    <div className="page narrow">
      <h1>Informe de auditoría</h1>
      <p className="muted">
        Pega el link de un Google Sheet ya rellenado (una copia de la plantilla de
        auditoría). La app lee las pestañas de trabajo, ignora las de ejemplo y
        genera el informe visual para el cliente. No añade ni interpreta nada — solo
        transforma lo que ya escribiste en la hoja.
      </p>
      <form onSubmit={handleSubmit}>
        <div className="row">
          <input
            type="url"
            required
            placeholder="https://docs.google.com/spreadsheets/d/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Generando..." : "Generar informe"}
          </button>
        </div>
      </form>
      {error && <p className="error">{error}</p>}
      <p className="muted small" style={{ marginTop: "1.5rem" }}>
        El Sheet tiene que estar compartido (lectura) con el email de la cuenta de
        servicio de Google configurada en el backend.
      </p>
    </div>
  );
}
