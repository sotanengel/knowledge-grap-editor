/**
 * The Turtle view (FR-09), editable and synchronised both ways.
 *
 * The graph is exported into the editor whenever it changes; saving pushes the
 * whole data graph back as one update. A syntax error comes back with a line
 * number, which is shown next to the editor rather than as a bare message.
 */
import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import { buildUpdate, parseErrorLine } from '../../lib/turtleSync';
import { useGraph } from '../../state/graph';
import { ErrorNote } from '../layout/ErrorNote';
import { Editor } from './Editor';

export function TurtleView() {
  const { entities, refresh } = useGraph();
  const [text, setText] = useState('');
  const [saved, setSaved] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorLine, setErrorLine] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const turtle = await api.exportGraph('turtle', ['urn:ontoforge:data']);
      setText(turtle);
      setSaved(turtle);
      setError(null);
      setErrorLine(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }, []);

  // Graph → text. `entities` changes whenever anything is written.
  useEffect(() => {
    void load();
  }, [load, entities]);

  const dirty = text !== saved;

  // Text → graph.
  const save = async () => {
    setBusy(true);
    setError(null);
    setErrorLine(null);
    setNote(null);
    try {
      const result = await api.sparqlUpdate(buildUpdate(text));
      setSaved(text);
      setNote(`保存しました（+${result.additions} / -${result.deletions}）`);
      await refresh();
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      setErrorLine(parseErrorLine(message));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-slate-200 px-2 py-1 dark:border-slate-800">
        <button
          type="button"
          onClick={() => void save()}
          disabled={busy || !dirty}
          className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-40"
        >
          {busy ? '保存中…' : 'グラフに反映'}
        </button>
        <button
          type="button"
          onClick={() => void load()}
          disabled={busy}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs dark:border-slate-600"
        >
          編集を破棄
        </button>
        {dirty && <span className="text-xs text-amber-600">未保存の変更があります</span>}
        {note && !dirty && <span className="text-xs text-slate-500">{note}</span>}
      </div>

      {error && (
        <div className="border-b border-red-200 px-2 py-1 dark:border-red-900">
          <ErrorNote message={errorLine ? `${errorLine} 行目: ${error}` : error} />
        </div>
      )}

      <div className="min-h-0 flex-1">
        <Editor
          value={text}
          language="turtle"
          onChange={setText}
          onSubmit={() => void save()}
          ariaLabel="Turtle"
        />
      </div>
    </div>
  );
}
