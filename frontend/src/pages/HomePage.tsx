import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, OntologyClass } from "../api/client";

export default function HomePage() {
  const [nodeCount, setNodeCount] = useState(0);
  const [classCount, setClassCount] = useState(0);
  const [classes, setClasses] = useState<OntologyClass[]>([]);
  const [quickQuery, setQuickQuery] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([api.listNodes(), api.listClasses()])
      .then(([nodes, cls]) => {
        setNodeCount(nodes.length);
        setClassCount(cls.length);
        setClasses(cls.slice(0, 6));
        setError("");
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "データの取得に失敗しました");
      });
  }, []);

  const handleQuickSearch = () => {
    const q = quickQuery.trim();
    navigate(q ? `/browse?q=${encodeURIComponent(q)}` : "/browse");
  };

  return (
    <main className="page home-page">
      <section className="hero">
        <h2>ナレッジグラフへようこそ</h2>
        <p>ノードと関係を登録し、グラフとして閲覧・編集できます。</p>
      </section>
      <section className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{nodeCount}</span>
          <span className="stat-label">ノード数</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{classCount}</span>
          <span className="stat-label">型の数</span>
        </div>
      </section>
      <section className="quick-search">
        <h3>クイック検索</h3>
        <div className="search-row">
          <input
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
            placeholder="ノード名で検索..."
            onKeyDown={(e) => e.key === "Enter" && handleQuickSearch()}
          />
          <button type="button" onClick={handleQuickSearch}>
            閲覧で検索
          </button>
        </div>
      </section>
      <section className="quick-actions">
        <Link to="/browse" className="action-card">
          <strong>閲覧</strong>
          <span>グラフの検索・編集</span>
        </Link>
        <Link to="/register" className="action-card">
          <strong>登録</strong>
          <span>ノード・関係の新規登録</span>
        </Link>
      </section>
      {error && <p className="error">{error}</p>}
      {classes.length > 0 && (
        <section>
          <h3>よく使う型</h3>
          <ul className="type-chips">
            {classes.map((c) => (
              <li key={c.id}>
                {c.label} <span>({c.id})</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
