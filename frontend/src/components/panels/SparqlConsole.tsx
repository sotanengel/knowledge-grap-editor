/** The SPARQL console (FR-07): run a query, see the rows or the Turtle. */
import { useState } from 'react';

import { api } from '../../api/client';
import type { SparqlResults } from '../../api/types';
import { useGraph } from '../../state/graph';
import { ErrorNote } from '../layout/ErrorNote';
import { Editor } from './Editor';

const STARTER = `SELECT ?item ?label WHERE {
  GRAPH <urn:ontoforge:data> {
    ?item <http://www.w3.org/2000/01/rdf-schema#label> ?label .
  }
} LIMIT 50`;

export function SparqlConsole() {
  const { select } = useGraph();
  const [query, setQuery] = useState(STARTER);
  const [results, setResults] = useState<SparqlResults | null>(null);
  const [turtle, setTurtle] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    setError(null);
    setResults(null);
    setTurtle(null);
    try {
      const result = await api.sparql(query);
      if (result.kind === 'results') setResults(result.results);
      else setTurtle(result.turtle);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const columns = results?.head.vars ?? [];
  const rows = results?.results?.bindings ?? [];

  return (
    <div className="flex h-full">
      <div className="flex w-1/2 flex-col border-r border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 border-b border-slate-200 px-2 py-1 dark:border-slate-800">
          <button
            type="button"
            onClick={() => void run()}
            disabled={busy}
            className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white disabled:opacity-50"
          >
            {busy ? '実行中…' : '実行 (⌘/Ctrl+Enter)'}
          </button>
        </div>
        <Editor
          value={query}
          language="sparql"
          onChange={setQuery}
          onSubmit={() => void run()}
          ariaLabel="SPARQL クエリ"
        />
      </div>

      <div className="w-1/2 overflow-auto p-2 text-xs">
        <ErrorNote message={error} />
        {results?.boolean !== undefined && (
          <p className="font-medium">結果: {results.boolean ? 'はい' : 'いいえ'}</p>
        )}
        {turtle !== null && <pre className="whitespace-pre-wrap font-mono">{turtle}</pre>}
        {rows.length > 0 && (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    className="border-b border-slate-300 px-2 py-1 text-left font-semibold dark:border-slate-700"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index} className="odd:bg-slate-50 dark:odd:bg-slate-800/50">
                  {columns.map((column) => {
                    const cell = row[column];
                    if (!cell)
                      return (
                        <td key={column} className="px-2 py-1 text-slate-400">
                          —
                        </td>
                      );
                    return (
                      <td key={column} className="px-2 py-1">
                        {cell.type === 'uri' ? (
                          <button
                            type="button"
                            onClick={() => select(cell.value)}
                            className="text-blue-700 hover:underline dark:text-blue-300"
                          >
                            {cell.value}
                          </button>
                        ) : (
                          cell.value
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!error && rows.length === 0 && turtle === null && results?.boolean === undefined && (
          <p className="text-slate-500">クエリを実行すると、ここに結果が出ます。</p>
        )}
        {results && rows.length === 0 && results.boolean === undefined && (
          <p className="text-slate-500">該当はありませんでした。</p>
        )}
      </div>
    </div>
  );
}
