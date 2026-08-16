export default function SearchPage() {
  return (
    <div className="page-content">
      <h2>検索</h2>
      <p className="hint">ノード・型・属性を横断検索します。</p>
      <div className="search-row">
        <input placeholder="ノード・型・属性を検索" aria-label="検索" />
        <button type="button">検索</button>
      </div>
    </div>
  );
}
