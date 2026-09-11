import { Routes, Route, Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import VideoDetail from "./pages/VideoDetail";
import History from "./pages/History";

function Nav() {
  return (
    <nav className="nav">
      <Link to="/" className="brand">
        Analizador de Videos
      </Link>
      <Link to="/">Nuevo análisis</Link>
      <Link to="/history">Historial</Link>
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
      </Routes>
    </>
  );
}
