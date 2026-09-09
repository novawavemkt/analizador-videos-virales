import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createVideo } from "../api";

export default function Dashboard() {
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [notas, setNotas] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { id } = await createVideo(url, notas);
      navigate(`/videos/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido.");
      setLoading(false);
    }
  }

  return (
    <div className="page narrow">
      <h1>Analizador de vídeos virales</h1>
      <p className="muted">
        Pega el link de un reel de TikTok o Instagram para analizar su hook,
        formato, nicho y nivel de conciencia (Schwartz).
      </p>
      <form onSubmit={handleSubmit}>
        <div className="row">
          <input
            type="url"
            required
            placeholder="https://www.tiktok.com/@usuario/video/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <button type="submit" disabled={loading}>
            {loading ? "Enviando..." : "Analizar"}
          </button>
        </div>
        <textarea
          placeholder="Notas manuales (opcional): contexto, resultados reales, cliente, sector..."
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          rows={3}
          className="notas-textarea"
        />
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
