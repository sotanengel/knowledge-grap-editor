import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Node } from "../api/client";
import SearchPanel from "../features/navigator/SearchPanel";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Node[]>([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    try {
      const result = await api.searchGraph(q);
      setResults(result.nodes);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "検索に失敗しました");
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => handleSearch(query), 300);
    return () => clearTimeout(t);
  }, [query, handleSearch]);

  return (
    <div className="page-content">
      <h2>検索</h2>
      <SearchPanel
        query={query}
        onQueryChange={setQuery}
        onSearch={handleSearch}
        results={results}
        onSelectResult={(node) => navigate(`/?focus=${encodeURIComponent(node.id)}`)}
      />
      {error && <p className="error">{error}</p>}
    </div>
  );
}
