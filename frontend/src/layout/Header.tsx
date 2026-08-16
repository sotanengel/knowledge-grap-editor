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

  const navClass = (paths: string[]) =>
    paths.some((p) => location.pathname === p) ? "nav-link active" : "nav-link";

  const isActive = (paths: string[]) =>
    paths.some((p) => location.pathname === p) ? "page" : undefined;

  return (
    <header className="app-header">
      <div className="header-brand">
        <Link to="/" className="brand-link">
          <span className="brand-icon" aria-hidden="true">
            ◉
          </span>
          ナレッジグラフ
        </Link>
      </div>
      <nav className="header-nav" aria-label="メインナビゲーション">
        <Link to="/" className={navClass(["/", "/browse"])} aria-current={isActive(["/", "/browse"])}>
          グラフ
        </Link>
        <Link
          to="/search"
          className={navClass(["/search"])}
          aria-current={isActive(["/search"])}
        >
          検索
        </Link>
        <Link
          to="/ontology"
          className={navClass(["/ontology"])}
          aria-current={isActive(["/ontology"])}
        >
          オントロジー
        </Link>
      </nav>
      <div className="header-actions">
        <button type="button" className="btn-header btn-secondary" disabled title="準備中">
          Import
        </button>
        <select
          value=""
          onChange={(e) => e.target.value && handleExport(e.target.value)}
          aria-label="Export形式"
        >
          <option value="">Export</option>
          <option value="turtle">Turtle</option>
          <option value="nt">N-Triples</option>
          <option value="jsonld">JSON-LD</option>
          <option value="xml">RDF/XML</option>
        </select>
      </div>
    </header>
  );
}
