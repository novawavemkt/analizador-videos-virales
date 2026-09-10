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
  created_at: string;
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
): Promise<{ video: VideoData; segments: Segment[]; frames: Frame[] }> {
  const res = await fetch(`${API_BASE}/api/videos/${id}`);
  return res.json();
}

export function frameUrl(videoId: number, frameId: number) {
  return `${API_BASE}/api/videos/${videoId}/frames/${frameId}`;
}

// --- Feature 2: informes de auditoria ---

export interface AuditSummary {
  id: number;
  cliente: string | null;
  sheet_url: string;
  created_at: string;
  updated_at: string;
}

export async function createAudit(sheetUrl: string): Promise<{ id: number; cliente: string | null }> {
  const res = await fetch(`${API_BASE}/api/audits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sheet_url: sheetUrl }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo generar el informe.");
  }
  return res.json();
}

export async function refreshAudit(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/audits/${id}/refresh`, { method: "POST" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo actualizar el informe.");
  }
}

export async function listAudits(): Promise<AuditSummary[]> {
  const res = await fetch(`${API_BASE}/api/audits`);
  const data = await res.json();
  return data.audits;
}

export async function getAudit(id: string): Promise<{ id: number; cliente: string | null; sheet_url: string }> {
  const res = await fetch(`${API_BASE}/api/audits/${id}`);
  if (!res.ok) throw new Error("No encontrado.");
  return res.json();
}

export function auditReportUrl(id: number | string) {
  return `${API_BASE}/api/audits/${id}/report`;
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
