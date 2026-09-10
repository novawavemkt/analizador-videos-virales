import { Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import VideoDetail from "./pages/VideoDetail";
import History from "./pages/History";
import AuditForm from "./pages/AuditForm";
import AuditReport from "./pages/AuditReport";
import AuditList from "./pages/AuditList";

function Nav() {
  return (
    <nav className="nav">
      <Link to="/" className="brand">
        Novawave
      </Link>
      <Link to="/">Analizador de vídeo</Link>
      <Link to="/history">Historial vídeo</Link>
      <Link to="/auditoria">Auditoría</Link>
      <Link to="/auditorias">Informes</Link>
    </nav>
  );
}

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/videos/:id" element={<VideoDetail />} />
        <Route path="/history" element={<History />} />
        <Route path="/auditoria" element={<AuditForm />} />
        <Route path="/auditoria/:id" element={<AuditReport />} />
        <Route path="/auditorias" element={<AuditList />} />
      </Routes>
    </>
  );
}
