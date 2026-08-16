interface Props {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSearch: () => void;
  depth: number;
  onDepthChange: (d: number) => void;
  onAddNode?: () => void;
  onAddRelationship?: () => void;
}

export default function LeftNavigator({
  searchQuery,
  onSearchChange,
  onSearch,
  depth,
  onDepthChange,
  onAddNode,
  onAddRelationship,
}: Props) {
  return (
    <div className="navigator-panel" data-testid="left-navigator">
      <section>
        <h3>検索</h3>
        <div className="search-row">
          <input
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="ノード・型・属性を検索"
            onKeyDown={(e) => e.key === "Enter" && onSearch()}
            aria-label="グラフ検索"
          />
          <button type="button" onClick={onSearch}>
            検索
          </button>
        </div>
        <label>
          探索深度
          <select
            value={depth}
            onChange={(e) => onDepthChange(Number(e.target.value))}
            aria-label="探索深度"
          >
            <option value={1}>1-hop</option>
            <option value={2}>2-hop</option>
            <option value={3}>3-hop</option>
          </select>
        </label>
      </section>
      <section>
        <div className="btn-row">
          <button type="button" onClick={onAddNode}>
            + Node
          </button>
          <button type="button" className="btn-secondary" onClick={onAddRelationship}>
            + Relationship
          </button>
        </div>
      </section>
    </div>
  );
}
