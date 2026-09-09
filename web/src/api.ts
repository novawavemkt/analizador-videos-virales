const API_BASE = "http://localhost:8000";

export interface VideoData {
  id: number;
  url: string;
  platform: string | null;
  autor: string | null;
  status: "pending" | "processing" | "done" | "error";
  error_message: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  like_count: number | null;
  hook: string | null;
  formato: string | null;
  nicho: string | null;
  awareness_overall: string | null;
  funciona_porque: string | null;
  aprendizaje_clave: string | null;
  transcript: string | null;
  notas_manuales: string | null;
  informe_markdown: string | null;
  puntuacion_media: number | null;
  created_at: string;
}

export interface Segment {
  id: number;
  start_seconds: number;
  end_seconds: number;
  text: string | null;
  awareness_stage: string;
}

export interface Frame {
  id: number;
  timestamp_seconds: number;
}

export async function createVideo(
  url: string,
  notasManuales?: string
): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE}/api/videos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, notas_manuales: notasManuales || null }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo crear el análisis.");
  }
  return res.json();
}

export async function reanalyzeVideo(id: number, notasManuales?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/videos/${id}/reanalyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notas_manuales: notasManuales || null }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo regenerar el análisis.");
  }
}

export async function listVideos(): Promise<VideoData[]> {
  const res = await fetch(`${API_BASE}/api/videos`);
  const data = await res.json();
  return data.videos;
}

export async function getVideo(
  id: string
): Promise<{ video: VideoData; segments: Segment[]; frames: Frame[] }> {
  const res = await fetch(`${API_BASE}/api/videos/${id}`);
  return res.json();
}

export function frameUrl(videoId: number, frameId: number) {
  return `${API_BASE}/api/videos/${videoId}/frames/${frameId}`;
}
