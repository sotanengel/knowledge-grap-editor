/** The change log, plus undo and redo (FR-12, §6.4). */
import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { HistoryPage } from '../../api/types';
import { useGraph } from '../../state/graph';
import { ErrorNote } from '../layout/ErrorNote';

const ACTOR_LABELS: Record<string, string> = {
  user: '手入力',
  reasoner: '推論',
  'sparql-update': 'Turtle / SPARQL',
};

function describeActor(actor: string): string {
  if (ACTOR_LABELS[actor]) return ACTOR_LABELS[actor];
  if (actor.startsWith('import:')) return `取り込み（${actor.slice('import:'.length)}）`;
  return actor;
}

export function HistoryPanel() {
  const { entities, refresh } = useGraph();
  const [page, setPage] = useState<HistoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api
      .history()
      .then(setPage)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)));
  }, []);

  useEffect(() => {
    load();
  }, [load, entities]);

  const step = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
      load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-slate-200 px-2 py-1 dark:border-slate-800">
        <button
          type="button"
          disabled={busy || !page?.can_undo}
          onClick={() => void step(api.undo)}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs disabled:opacity-40 dark:border-slate-600"
        >
          元に戻す
        </button>
        <button
          type="button"
          disabled={busy || !page?.can_redo}
          onClick={() => void step(api.redo)}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs disabled:opacity-40 dark:border-slate-600"
        >
          やり直す
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-2">
        <ErrorNote message={error} />
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-2 py-1">#</th>
              <th className="px-2 py-1">操作</th>
              <th className="px-2 py-1">変更</th>
              <th className="px-2 py-1">時刻</th>
            </tr>
          </thead>
          <tbody>
            {(page?.entries ?? []).map((entry) => (
              <tr key={entry.id} className="odd:bg-slate-50 dark:odd:bg-slate-800/50">
                <td className="px-2 py-1">{entry.seq}</td>
                <td className="px-2 py-1">
                  {describeActor(entry.actor)}
                  {entry.inverse_of && <span className="ml-1 text-slate-400">（取り消し）</span>}
                </td>
                <td className="px-2 py-1">
                  <span className="text-emerald-600">+{entry.additions}</span>{' '}
                  <span className="text-red-600">−{entry.deletions}</span>
                </td>
                <td className="px-2 py-1 text-slate-500">
                  {new Date(entry.timestamp).toLocaleString('ja-JP')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {page?.entries.length === 0 && <p className="p-2 text-slate-500">まだ変更がありません。</p>}
      </div>
    </div>
  );
}
