import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAudits, type AuditSummary } from "../api";

export default function AuditList() {
  const [audits, setAudits] = useState<AuditSummary[]>([]);

  useEffect(() => {
    listAudits().then(setAudits);
  }, []);

  return (
    <div className="page wide">
      <h1>Informes de auditoría</h1>
      <div className="list">
        {audits.map((a) => (
          <Link key={a.id} to={`/auditoria/${a.id}`} className="list-item">
            <div className="row" style={{ justifyContent: "space-between", marginTop: 0 }}>
              <strong>{a.cliente || "(sin nombre de cliente)"}</strong>
              <span className="muted small">{a.created_at}</span>
            </div>
            <span className="muted small truncate">{a.sheet_url}</span>
          </Link>
        ))}
        {audits.length === 0 && (
          <p className="muted">
            Todavía no hay informes. Ve a <Link to="/auditoria">Auditoría</Link> para generar el primero.
          </p>
        )}
      </div>
    </div>
  );
}
