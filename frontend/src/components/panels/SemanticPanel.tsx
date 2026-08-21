/**
 * Similar-label search (§14 Phase 3).
 *
 * Which similarity is being measured decides what a score means, so the panel
 * says which embedder produced it. With the trained embedding in the image,
 * 「企業」 finds 「株式会社アクメ」; with only the character n-gram fallback it
 * finds nothing there, and the panel says so rather than letting someone read
 * more into a number than is in it.
 */
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { SemanticHit, SemanticStatus } from '../../api/types';
import { useGraph } from '../../state/graph';
import { ErrorNote } from '../layout/ErrorNote';

export function SemanticPanel() {
  const { select } = useGraph();
  const [status, setStatus] = useState<SemanticStatus | null>(null);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SemanticHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .semanticStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  if (status && !status.enabled) {
    return (
      <div className="space-y-2 p-4 text-sm text-slate-600 dark:text-slate-300">
        <p>類似検索は既定で無効です。</p>
        <p className="text-xs text-slate-500">
          このイメージで使えるのは <strong>{status.embedder}</strong> です。{status.note}
        </p>
        <pre className="rounded bg-slate-100 p-2 text-xs dark:bg-slate-800">
          docker run -e ONTOFORGE_SEMANTIC_SEARCH=1 …
        </pre>
      </div>
    );
  }

  const run = async () => {
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setHits((await api.semanticSearch(query.trim())).results);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <form
        className="flex items-center gap-2 border-b border-slate-200 px-2 py-1 dark:border-slate-800"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="似ている名前を探す"
          className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
        >
          探す
        </button>
        {status && (
          <span className="text-xs text-slate-500">
            {status.indexed} 件を索引済み
            {status.quality === 'surface' && '（表記のゆれのみ）'}
          </span>
        )}
      </form>

      <div className="min-h-0 flex-1 overflow-auto p-2 text-sm">
        <ErrorNote message={error} />
        {status && (
          // Kept visible either way: a reader looking at 0.18 deserves to know
          // what kind of similarity produced it. Only the emphasis differs --
          // the surface fallback is weaker than the number suggests.
          <p
            className={`mb-2 text-[10px] ${
              status.quality === 'surface' ? 'text-amber-700 dark:text-amber-300' : 'text-slate-500'
            }`}
          >
            {status.note}
          </p>
        )}
        <ul className="space-y-1">
          {hits.map((hit) => (
            <li key={hit.iri} className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => select(hit.iri)}
                className="flex-1 truncate text-left text-blue-700 hover:underline dark:text-blue-300"
              >
                {hit.label}
              </button>
              <span className="w-14 text-right text-xs text-slate-500">{hit.score.toFixed(3)}</span>
            </li>
          ))}
        </ul>
        {!busy && hits.length === 0 && query && !error && (
          <p className="text-slate-500">近い名前は見つかりませんでした。</p>
        )}
      </div>
    </div>
  );
}
