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
  filtro_angulo_pasa: 0 | 1 | null;
  filtro_avatar_pasa: 0 | 1 | null;
  filtro_explicacion: string | null;
  potencial_viral: number | null;
  linked_video_id: number | null;
  created_at: string;
}

export interface LinkedVideoSummary {
  id: number;
  url: string;
  platform: string | null;
  status: string;
  view_count: number | null;
  like_count: number | null;
  puntuacion_media: number | null;
  potencial_viral: number | null;
  awareness_overall: string | null;
  hook: string | null;
}

export interface Comment {
  id: number;
  author: string | null;
  text: string;
  like_count: number | null;
}

export interface ClientProfile {
  autor: string;
  angulo: string | null;
  avatar: string | null;
  posicionamiento: string | null;
  updated_at: string | null;
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
): Promise<{
  video: VideoData;
  segments: Segment[];
  frames: Frame[];
  comments: Comment[];
  linked_video: LinkedVideoSummary | null;
}> {
  const res = await fetch(`${API_BASE}/api/videos/${id}`);
  return res.json();
}

export async function linkVideo(id: number, url: string): Promise<{ linked_video_id: number }> {
  const res = await fetch(`${API_BASE}/api/videos/${id}/link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo vincular el vídeo.");
  }
  return res.json();
}

export async function unlinkVideo(id: number): Promise<void> {
  await fetch(`${API_BASE}/api/videos/${id}/unlink`, { method: "POST" });
}

export function frameUrl(videoId: number, frameId: number) {
  return `${API_BASE}/api/videos/${videoId}/frames/${frameId}`;
}

export async function getClientProfile(autor: string): Promise<ClientProfile> {
  const res = await fetch(`${API_BASE}/api/clients/${encodeURIComponent(autor)}`);
  return res.json();
}

export async function saveClientProfile(
  autor: string,
  profile: { angulo: string; avatar: string; posicionamiento: string }
): Promise<void> {
  await fetch(`${API_BASE}/api/clients/${encodeURIComponent(autor)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
}
