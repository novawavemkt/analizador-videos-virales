import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  getVideo,
  reanalyzeVideo,
  frameUrl,
  listVideos,
  getClientProfile,
  saveClientProfile,
  linkVideo,
  unlinkVideo,
  type VideoData,
  type Segment,
  type Frame,
  type Comment,
  type LinkedVideoSummary,
} from "../api";
import { AWARENESS_LABELS, AWARENESS_COLORS } from "../awareness";

export default function VideoDetail() {
  const { id } = useParams<{ id: string }>();
  const [video, setVideo] = useState<VideoData | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [frames, setFrames] = useState<Frame[]>([]);
  const [notas, setNotas] = useState("");
  const [regenerating, setRegenerating] = useState(false);
  const [clientHistory, setClientHistory] = useState<VideoData[]>([]);
  const [angulo, setAngulo] = useState("");
  const [avatar, setAvatar] = useState("");
  const [posicionamiento, setPosicionamiento] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [linkedVideo, setLinkedVideo] = useState<LinkedVideoSummary | null>(null);
  const [linkUrl, setLinkUrl] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!id) return;
    const data = await getVideo(id);
    setVideo(data.video);
    setSegments(data.segments);
    setFrames(data.frames);
    setNotas(data.video.notas_manuales || "");
    setComments(data.comments || []);
    setLinkedVideo(data.linked_video || null);
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!video || video.status === "done" || video.status === "error") return;
    const interval = setInterval(fetchData, 2500);
    return () => clearInterval(interval);
  }, [video, fetchData]);

  useEffect(() => {
    if (!video || video.status !== "done" || !video.autor) {
      setClientHistory([]);
      return;
    }
    listVideos().then((all) => {
      setClientHistory(
        all.filter((v) => v.autor === video.autor && v.id !== video.id && v.status === "done")
      );
    });
  }, [video]);

  useEffect(() => {
    if (!video || video.status !== "done" || !video.autor) return;
    getClientProfile(video.autor).then((p) => {
      setAngulo(p.angulo || "");
      setAvatar(p.avatar || "");
      setPosicionamiento(p.posicionamiento || "");
    });
  }, [video?.id, video?.autor, video?.status]);

  async function handleSaveProfile() {
    if (!video?.autor) return;
    setSavingProfile(true);
    await saveClientProfile(video.autor, { angulo, avatar, posicionamiento });
    setSavingProfile(false);
    setProfileSaved(true);
    setTimeout(() => setProfileSaved(false), 2000);
  }

  async function handleLink() {
    if (!video || !linkUrl.trim()) return;
    setLinking(true);
    setLinkError(null);
    try {
      await linkVideo(video.id, linkUrl.trim());
      setLinkUrl("");
      await fetchData();
    } catch (err) {
      setLinkError(err instanceof Error ? err.message : "Error desconocido.");
    } finally {
      setLinking(false);
    }
  }

  async function handleUnlink() {
    if (!video) return;
    await unlinkVideo(video.id);
    setLinkedVideo(null);
  }

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
            Craft {video.puntuacion_media.toFixed(1)}/10
          </span>
        )}
        {video.potencial_viral != null && (
          <span className="badge" style={{ background: "#db2777" }}>
            Potencial viral {video.potencial_viral.toFixed(1)}/10
          </span>
        )}
        {video.filtro_angulo_pasa != null && (
          <span className="badge" style={{ background: video.filtro_angulo_pasa ? "#10b981" : "#ef4444" }}>
            {video.filtro_angulo_pasa ? "✓ Ángulo" : "✗ Ángulo"}
          </span>
        )}
        {video.filtro_avatar_pasa != null && (
          <span className="badge" style={{ background: video.filtro_avatar_pasa ? "#10b981" : "#ef4444" }}>
            {video.filtro_avatar_pasa ? "✓ Avatar" : "✗ Avatar"}
          </span>
        )}
      </div>

      {video.filtro_explicacion && (
        <p className="muted small" style={{ marginTop: "0.5rem" }}>
          {video.filtro_explicacion}
        </p>
      )}

      <section>
        <h2>Comparativa entre plataformas</h2>
        {linkedVideo ? (
          <>
            <p className="muted small">
              Este vídeo está vinculado con su versión en{" "}
              <Link to={`/videos/${linkedVideo.id}`}>{linkedVideo.platform || "otra plataforma"}</Link>.
            </p>
            <div className="tags small">
              {linkedVideo.view_count != null && <span className="badge">{linkedVideo.view_count.toLocaleString("es-ES")} vistas</span>}
              {linkedVideo.like_count != null && <span className="badge">{linkedVideo.like_count.toLocaleString("es-ES")} likes</span>}
              {linkedVideo.puntuacion_media != null && <span className="badge">Craft {linkedVideo.puntuacion_media.toFixed(1)}/10</span>}
              {linkedVideo.potencial_viral != null && <span className="badge">Viral {linkedVideo.potencial_viral.toFixed(1)}/10</span>}
              {linkedVideo.status !== "done" && <span className="badge">{linkedVideo.status}</span>}
            </div>
            <div className="row">
              <button type="button" onClick={handleUnlink}>
                Quitar vínculo
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="muted small">
              ¿Este mismo vídeo está también publicado en otra plataforma (Instagram/TikTok)? Pega su
              link para verlo en el mismo sitio y comparar vistas, likes y puntuaciones entre las dos.
            </p>
            <div className="row">
              <input
                type="url"
                placeholder="https://www.tiktok.com/@usuario/video/... o link de Instagram"
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
              />
              <button type="button" onClick={handleLink} disabled={linking || !linkUrl.trim()}>
                {linking ? "Vinculando..." : "Vincular"}
              </button>
            </div>
            {linkError && <p className="error">{linkError}</p>}
          </>
        )}
      </section>

      {clientHistory.length > 0 && (
        <section>
          <h2>Historial de este cliente ({video.autor})</h2>
          <div className="list">
            {clientHistory.map((v) => (
              <Link key={v.id} to={`/videos/${v.id}`} className="list-item">
                <div className="row" style={{ justifyContent: "space-between", marginTop: 0 }}>
                  <span className="truncate">{v.hook || v.url}</span>
                  {v.puntuacion_media != null && (
                    <span className="muted small">{v.puntuacion_media.toFixed(1)}/10</span>
                  )}
                </div>
                <div className="tags small">
                  {v.formato && <span className="badge">{v.formato}</span>}
                  {v.awareness_overall && (
                    <span className="badge">{AWARENESS_LABELS[v.awareness_overall] || v.awareness_overall}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            El informe de arriba ya tiene en cuenta este historial al generarse.
          </p>
        </section>
      )}

      {video.autor && (
        <section>
          <h2>Perfil del cliente ({video.autor}) — ángulo / avatar / posicionamiento</h2>
          <p className="muted small">
            Definelo una vez para esta cuenta y todos sus vídeos se evaluarán contra este perfil
            (filtro de ángulo/avatar, Módulo 1-2 Nova Wave). Guarda y regenera el análisis para
            que el informe lo tenga en cuenta.
          </p>
          <textarea
            value={angulo}
            onChange={(e) => setAngulo(e.target.value)}
            placeholder="Ángulo: hablar de [tema] desde [perspectiva] para ayudar a [audiencia] a conseguir [resultado]"
            rows={2}
          />
          <textarea
            value={avatar}
            onChange={(e) => setAvatar(e.target.value)}
            placeholder="Avatar: cómo es, cómo piensa, qué le duele, qué quiere..."
            rows={2}
          />
          <textarea
            value={posicionamiento}
            onChange={(e) => setPosicionamiento(e.target.value)}
            placeholder="Posicionamiento: atributo de relación / autoridad / diferenciador"
            rows={2}
          />
          <div className="row">
            <button onClick={handleSaveProfile} disabled={savingProfile}>
              {savingProfile ? "Guardando..." : profileSaved ? "Guardado ✓" : "Guardar perfil"}
            </button>
          </div>
        </section>
      )}

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

      {comments.length > 0 && (
        <section>
          <h2>Comentarios reales ({comments.length})</h2>
          <div className="list">
            {comments.map((c) => (
              <div key={c.id} className="list-item">
                <div className="row" style={{ justifyContent: "space-between", marginTop: 0 }}>
                  <strong>{c.author || "anónimo"}</strong>
                  {c.like_count != null && <span className="muted small">{c.like_count} likes</span>}
                </div>
                <p className="muted" style={{ margin: "0.25rem 0 0" }}>{c.text}</p>
              </div>
            ))}
          </div>
          <p className="muted small" style={{ marginTop: "0.5rem" }}>
            El informe de arriba ya incluye un análisis de estos comentarios (sección 12).
          </p>
        </section>
      )}

      {video.transcript && (
        <section>
          <h2>Transcripción completa</h2>
          <p className="muted pre">{video.transcript}</p>
        </section>
      )}
    </div>
  );
}
