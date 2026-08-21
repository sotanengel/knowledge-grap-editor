/** Search, reasoning, validation, export and the terminology switch (§7.1). */
import { useState } from 'react';

import { api } from '../../api/client';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { ErrorNote } from './ErrorNote';
import { ProjectSwitcher } from './ProjectSwitcher';

const EXPORT_FORMATS = [
  { value: 'turtle', label: 'Turtle (.ttl)' },
  { value: 'trig', label: 'TriG (.trig)' },
  { value: 'jsonld', label: 'JSON-LD' },
  { value: 'nquads', label: 'N-Quads' },
  { value: 'rdfxml', label: 'RDF/XML' },
  { value: 'graphml', label: 'GraphML (Gephi / yEd)' },
  { value: 'csv', label: 'CSV ノード表＋エッジ表' },
  { value: 'mermaid', label: 'Mermaid' },
];

export function Header({ onOpenPanel }: { onOpenPanel: (tab: string) => void }) {
  const { query, setQuery, refresh, setValidation, entities } = useGraph();
  const { terms, terminology, setTerminology, showDetails, setShowDetails, health } = useSettings();
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (name: string, action: () => Promise<string>) => {
    setBusy(name);
    setError(null);
    try {
      setNote(await action());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(null);
    }
  };

  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-slate-900">
      <h1 className="text-base font-semibold">OntoForge</h1>

      <ProjectSwitcher />

      <label className="flex-1 min-w-[200px] max-w-md">
        <span className="sr-only">検索</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`${terms.instance}を名前で検索`}
          className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </label>

      <button
        type="button"
        disabled={busy !== null}
        onClick={() =>
          run('reason', async () => {
            const summary = await api.reason();
            await refresh();
            onOpenPanel('turtle');
            const held = summary.suppressed > 0 ? `、${summary.suppressed} 件は表示を省略` : '';
            return `推論: ${summary.derived} 件を導出（${summary.profile}）${held}`;
          })
        }
        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
      >
        推論実行
      </button>

      <button
        type="button"
        disabled={busy !== null}
        onClick={() =>
          run('validate', async () => {
            const report = await api.validate();
            setValidation(report);
            onOpenPanel('validation');
            return report.conforms
              ? '検証: 違反はありません'
              : `検証: ${report.findings.length} 件の違反`;
          })
        }
        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
      >
        検証
      </button>

      <label className="flex items-center gap-1 text-sm">
        <span className="sr-only">エクスポート形式</span>
        <select
          defaultValue=""
          onChange={(event) => {
            if (!event.target.value) return;
            window.open(api.exportUrl(event.target.value), '_blank', 'noopener');
            event.target.value = '';
          }}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        >
          <option value="">エクスポート…</option>
          {EXPORT_FORMATS.map((format) => (
            <option key={format.value} value={format.value}>
              {format.label}
            </option>
          ))}
        </select>
      </label>

      <div className="ml-auto flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
        <span>{entities.length} 件</span>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={terminology === 'technical'}
            onChange={(event) => setTerminology(event.target.checked ? 'technical' : 'plain')}
          />
          専門用語表記
        </label>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={showDetails}
            onChange={(event) => setShowDetails(event.target.checked)}
          />
          詳細
        </label>
        {health && showDetails && <span title={health.base_iri}>推論: {health.reasoner}</span>}
      </div>

      {(note || error) && (
        <div className="w-full">
          <ErrorNote message={error} />
          {note && !error && (
            <p role="status" className="text-xs text-slate-600 dark:text-slate-300">
              {note}
            </p>
          )}
        </div>
      )}
    </header>
  );
}
