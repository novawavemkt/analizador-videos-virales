import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { getVideo, reanalyzeVideo, frameUrl, type VideoData, type Segment, type Frame } from "../api";
import { AWARENESS_LABELS, AWARENESS_COLORS } from "../awareness";

export default function VideoDetail() {
  const { id } = useParams<{ id: string }>();
  const [video, setVideo] = useState<VideoData | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [frames, setFrames] = useState<Frame[]>([]);
  const [notas, setNotas] = useState("");
  const [regenerating, setRegenerating] = useState(false);

  const fetchData = useCallback(async () => {
    if (!id) return;
    const data = await getVideo(id);
    setVideo(data.video);
    setSegments(data.segments);
    setFrames(data.frames);
    setNotas(data.video.notas_manuales || "");
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!video || video.status === "done" || video.status === "error") return;
    const interval = setInterval(fetchData, 2500);
    return () => clearInterval(interval);
  }, [video, fetchData]);

  async function handleRegenerate() {
    if (!video) return;
    setRegenerating(true);
    await reanalyzeVideo(video.id, notas);
    // Actualizacion optimista: el estado real en BD lo pone el hilo en
    // background, que puede tardar un instante en arrancar. Sin esto, un
    // fetch inmediato podria ver todavia el estado 'done' anterior y no
    // activar el polling.
    setVideo((prev) => (prev ? { ...prev, status: "processing" } : prev));
    setRegenerating(false);
  }

  if (!video) return <div className="page narrow muted">Cargando...</div>;

  if (video.status === "pending" || video.status === "processing") {
    return (
      <div className="page narrow">
        <p className="muted break">{video.url}</p>
        <div className="row" style={{ alignItems: "center" }}>
          <div className="spinner" />
          {video.status === "pending" ? "En cola..." : "Descargando, transcribiendo y clasificando..."}
        </div>
      </div>
    );
  }

  if (video.status === "error") {
    return (
      <div className="page narrow">
        <p className="muted break">{video.url}</p>
        <p className="error">Error al procesar: {video.error_message}</p>
      </div>
    );
  }

  return (
    <div className="page">
      <a href={video.url} target="_blank" rel="noreferrer" className="link break">
        {video.url}
      </a>

      <div className="tags">
        {video.duration_seconds != null && <span>{Math.round(video.duration_seconds)}s</span>}
        {video.view_count != null && <span>{video.view_count.toLocaleString("es-ES")} vistas</span>}
        {video.like_count != null && <span>{video.like_count.toLocaleString("es-ES")} likes</span>}
        {video.autor && <span className="badge">{video.autor}</span>}
        {video.nicho && <span className="badge">{video.nicho}</span>}
        {video.formato && <span className="badge">{video.formato}</span>}
        {video.puntuacion_media != null && (
          <span className="badge" style={{ background: "#4f46e5" }}>
            {video.puntuacion_media.toFixed(1)}/10
          </span>
        )}
      </div>

      {video.awareness_overall && (
        <section>
          <h2>Nivel de conciencia (general)</h2>
          <span
            className="badge big"
            style={{ background: AWARENESS_COLORS[video.awareness_overall] || "#374151" }}
          >
            {AWARENESS_LABELS[video.awareness_overall] || video.awareness_overall}
          </span>
        </section>
      )}

      {frames.length > 0 && (
        <div className="frames">
          {frames.map((f) => (
            <img key={f.id} src={frameUrl(video.id, f.id)} alt={`Fotograma a los ${f.timestamp_seconds}s`} />
          ))}
        </div>
      )}

      {segments.length > 0 && (
        <section>
          <h2>Desglose por tramos de conciencia</h2>
          <div className="segments">
            {segments.map((s) => (
              <div key={s.id} className="segment">
                <span className="segment-time">
                  {Math.round(s.start_seconds)}s–{Math.round(s.end_seconds)}s
                </span>
                <div>
                  <span
                    className="badge"
                    style={{ background: AWARENESS_COLORS[s.awareness_stage] || "#374151" }}
                  >
                    {AWARENESS_LABELS[s.awareness_stage] || s.awareness_stage}
                  </span>
                  {s.text && <p className="segment-text">{s.text}</p>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {video.informe_markdown && (
        <section>
          <h2>Informe completo</h2>
          <div className="report">
            <ReactMarkdown>{video.informe_markdown}</ReactMarkdown>
          </div>
        </section>
      )}

      <section>
        <h2>Notas manuales</h2>
        <textarea
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          placeholder="Añade contexto, resultados reales, correcciones... y regenera el análisis."
          rows={4}
        />
        <div className="row">
          <button onClick={handleRegenerate} disabled={regenerating}>
            {regenerating ? "Regenerando..." : "Regenerar análisis"}
          </button>
        </div>
      </section>

      {video.transcript && (
        <section>
          <h2>Transcripción completa</h2>
          <p className="muted pre">{video.transcript}</p>
        </section>
      )}
    </div>
  );
}
