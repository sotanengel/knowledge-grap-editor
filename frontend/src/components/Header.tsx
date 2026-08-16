import { Link, useLocation } from "react-router-dom";
import { api } from "../api/client";

export default function Header() {
  const location = useLocation();

  const handleExport = async (format: string) => {
    const blob = await api.exportRdf(format);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `knowledge-graph.${format === "jsonld" ? "jsonld" : format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const navClass = (path: string) =>
    location.pathname === path ? "nav-link active" : "nav-link";

  return (
    <header className="app-header">
      <div className="header-brand">
        <Link to="/" className="brand-link">
          ナレッジグラフ
        </Link>
      </div>
      <nav className="header-nav" aria-label="メインナビゲーション">
        <Link to="/" className={navClass("/")} aria-current={location.pathname === "/" ? "page" : undefined}>
          ホーム
        </Link>
        <Link
          to="/browse"
          className={navClass("/browse")}
          aria-current={location.pathname === "/browse" ? "page" : undefined}
        >
          閲覧
        </Link>
        <Link
          to="/register"
          className={navClass("/register")}
          aria-current={location.pathname === "/register" ? "page" : undefined}
        >
          登録
        </Link>
      </nav>
      <div className="header-actions">
        <select
          value=""
          onChange={(e) => e.target.value && handleExport(e.target.value)}
          aria-label="Export形式"
        >
          <option value="">Export...</option>
          <option value="turtle">Turtle</option>
          <option value="nt">N-Triples</option>
          <option value="jsonld">JSON-LD</option>
          <option value="xml">RDF/XML</option>
        </select>
      </div>
    </header>
  );
}
