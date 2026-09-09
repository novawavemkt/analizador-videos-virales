import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listVideos, type VideoData } from "../api";
import { AWARENESS_LABELS, AWARENESS_STAGES } from "../awareness";

const PLATFORM_LABELS: Record<string, string> = {
  tiktok: "TikTok",
  instagram: "Instagram",
  otro: "Otro",
};

export default function History() {
  const [videos, setVideos] = useState<VideoData[]>([]);
  const [platformFilter, setPlatformFilter] = useState<string>("");
  const [awarenessFilter, setAwarenessFilter] = useState<string>("");
  const [autorQuery, setAutorQuery] = useState("");
  const [nichoFilter, setNichoFilter] = useState("");
  const [formatoFilter, setFormatoFilter] = useState("");

  useEffect(() => {
    listVideos().then(setVideos);
  }, []);

  const platforms = useMemo(
    () => Array.from(new Set(videos.map((v) => v.platform).filter(Boolean))) as string[],
    [videos]
  );
  const nichos = useMemo(
    () => Array.from(new Set(videos.map((v) => v.nicho).filter(Boolean))) as string[],
    [videos]
  );
  const formatos = useMemo(
    () => Array.from(new Set(videos.map((v) => v.formato).filter(Boolean))) as string[],
    [videos]
  );

  const filtered = videos.filter(
    (v) =>
      (!platformFilter || v.platform === platformFilter) &&
      (!awarenessFilter || v.awareness_overall === awarenessFilter) &&
      (!nichoFilter || v.nicho === nichoFilter) &&
      (!formatoFilter || v.formato === formatoFilter) &&
      (!autorQuery || (v.autor || "").toLowerCase().includes(autorQuery.toLowerCase()))
  );

  return (
    <div className="page wide">
      <h1>Historial</h1>

      <div className="tabs">
        <button className={platformFilter === "" ? "tab active" : "tab"} onClick={() => setPlatformFilter("")}>
          Todos
        </button>
        {platforms.map((p) => (
          <button
            key={p}
            className={platformFilter === p ? "tab active" : "tab"}
            onClick={() => setPlatformFilter(p)}
          >
            {PLATFORM_LABELS[p] || p}
          </button>
        ))}
      </div>

      <div className="tabs">
        <button className={awarenessFilter === "" ? "tab active" : "tab"} onClick={() => setAwarenessFilter("")}>
          Todas las etapas
        </button>
        {AWARENESS_STAGES.map((stage) => (
          <button
            key={stage}
            className={awarenessFilter === stage ? "tab active" : "tab"}
            onClick={() => setAwarenessFilter(stage)}
          >
            {AWARENESS_LABELS[stage]}
          </button>
        ))}
      </div>

      <div className="row">
        <input
          type="text"
          placeholder="Buscar por usuario (@cuenta)..."
          value={autorQuery}
          onChange={(e) => setAutorQuery(e.target.value)}
        />
        <select value={nichoFilter} onChange={(e) => setNichoFilter(e.target.value)}>
          <option value="">Todos los nichos</option>
          {nichos.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <select value={formatoFilter} onChange={(e) => setFormatoFilter(e.target.value)}>
          <option value="">Todos los formatos</option>
          {formatos.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
      </div>

      <div className="list">
        {filtered.map((v) => (
          <Link key={v.id} to={`/videos/${v.id}`} className="list-item">
            <div className="row" style={{ justifyContent: "space-between", marginTop: 0 }}>
              <span className="truncate">{v.url}</span>
              <span className="muted small">{v.status}</span>
            </div>
            {v.hook && <p className="muted truncate">{v.hook}</p>}
            <div className="tags small">
              {v.platform && <span className="badge">{PLATFORM_LABELS[v.platform] || v.platform}</span>}
              {v.autor && <span className="badge">{v.autor}</span>}
              {v.nicho && <span className="badge">{v.nicho}</span>}
              {v.formato && <span className="badge">{v.formato}</span>}
              {v.awareness_overall && (
                <span className="badge">{AWARENESS_LABELS[v.awareness_overall] || v.awareness_overall}</span>
              )}
            </div>
          </Link>
        ))}
        {filtered.length === 0 && <p className="muted">No hay vídeos que coincidan con estos filtros.</p>}
      </div>
    </div>
  );
}
