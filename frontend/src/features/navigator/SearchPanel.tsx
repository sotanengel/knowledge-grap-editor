import { useEffect, useState } from "react";
import type { Node } from "../../api/client";

interface Props {
  query: string;
  onQueryChange: (q: string) => void;
  onSearch: (q: string) => void;
  results: Node[];
  onSelectResult: (node: Node) => void;
}

export default function SearchPanel({
  query,
  onQueryChange,
  onSearch,
  results,
  onSelectResult,
}: Props) {
  const [debounced, setDebounced] = useState(query);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(query);
      if (query.trim()) onSearch(query.trim());
    }, 300);
    return () => clearTimeout(t);
  }, [query, onSearch]);

  return (
    <section data-testid="search-panel">
      <h3>検索</h3>
      <input
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="ノード・型・属性を検索"
        aria-label="グラフ検索"
      />
      {debounced && (
        <div className="search-results-wrap">
          <p className="hint">{results.length} nodes</p>
          <ul className="search-results">
            {results.map((n) => (
              <li key={n.id} onClick={() => onSelectResult(n)}>
                <span className="search-result-type">{n.type}</span>
                <strong>{n.label}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
