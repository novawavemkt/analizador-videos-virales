import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { getAudit, refreshAudit, auditReportUrl } from "../api";

export default function AuditReport() {
  const { id } = useParams<{ id: string }>();
  const [cliente, setCliente] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [cacheBust, setCacheBust] = useState(0);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const a = await getAudit(id);
      setCliente(a.cliente);
    } catch {
      setNotFound(true);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRefresh() {
    if (!id) return;
    setBusy(true);
    setMsg(null);
    try {
      await refreshAudit(Number(id));
      setCacheBust((n) => n + 1);
      await load();
      setMsg("Actualizado desde el Sheet.");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "No se pudo actualizar.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload() {
    if (!id) return;
    const res = await fetch(auditReportUrl(id));
    const html = await res.text();
    const blob = new Blob([html], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `auditoria-${(cliente || id).toString().toLowerCase().replace(/\s+/g, "-")}.html`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (notFound) {
    return <div className="page narrow"><p className="error">Informe no encontrado.</p></div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 51px)" }}>
      <div
        className="row"
        style={{
          margin: 0,
          padding: "0.7rem 1.25rem",
          borderBottom: "1px solid #262626",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <strong style={{ flex: 1 }}>{cliente || "Informe de auditoría"}</strong>
        {msg && <span className="muted small">{msg}</span>}
        <a href={auditReportUrl(id!)} target="_blank" rel="noreferrer">
          <button type="button">Pantalla completa</button>
        </a>
        <button type="button" onClick={handleDownload}>
          Descargar HTML
        </button>
        <button type="button" onClick={handleRefresh} disabled={busy}>
          {busy ? "Actualizando..." : "Actualizar desde el Sheet"}
        </button>
      </div>
      <iframe
        ref={iframeRef}
        title="Informe de auditoría"
        src={`${auditReportUrl(id!)}?v=${cacheBust}`}
        style={{ flex: 1, width: "100%", border: "none", background: "#F2F1EA" }}
      />
    </div>
  );
}
