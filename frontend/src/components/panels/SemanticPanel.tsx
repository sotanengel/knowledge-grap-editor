/**
 * Similar-label search (§14 Phase 3).
 *
 * The panel says plainly what this is: a surface-similarity signal computed
 * locally from character n-grams, not a trained embedding. It is good at
 * finding 「田中太郎」 from 「田中」 or spotting near-duplicate labels, and it
 * does not understand meaning. Saying so is better than letting someone read
 * more into the scores than is there.
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
        <p className="text-xs text-slate-500">{status.note}</p>
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
        {status && <span className="text-xs text-slate-500">{status.indexed} 件を索引済み</span>}
      </form>

      <div className="min-h-0 flex-1 overflow-auto p-2 text-sm">
        <ErrorNote message={error} />
        {status && <p className="mb-2 text-[10px] text-slate-500">{status.note}</p>}
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
