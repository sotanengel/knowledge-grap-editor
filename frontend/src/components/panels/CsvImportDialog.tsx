/**
 * Mapping a table onto the graph (FR-13, §11).
 *
 * One row is one item; a named column is its identity, so re-importing the same
 * file updates rather than duplicates. The mapping itself can be saved and
 * reused next time the same export lands on the desk.
 */
import { useState } from 'react';

import { api } from '../../api/client';
import type { ColumnMapping, CsvMapping } from '../../api/types';
import { guessDelimiter, preview } from '../../lib/csv';
import { flattenTerms } from '../../lib/ontology';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { Dialog } from '../layout/Dialog';
import { ErrorNote } from '../layout/ErrorNote';

interface Props {
  onClose: () => void;
}

export function CsvImportDialog({ onClose }: Props) {
  const { ontology, refresh } = useGraph();
  const { terms } = useSettings();
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [delimiter, setDelimiter] = useState(',');
  const [name, setName] = useState('mapping');
  const [labelColumn, setLabelColumn] = useState('');
  const [keyColumn, setKeyColumn] = useState('');
  const [type, setType] = useState('');
  const [columns, setColumns] = useState<ColumnMapping[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const table = text ? preview(text, delimiter) : { header: [], rows: [] };

  const onFile = async (chosen: File | null) => {
    setFile(chosen);
    setNote(null);
    if (!chosen) return;
    const content = await chosen.text();
    const guessed = guessDelimiter(content);
    const { header } = preview(content, guessed);
    setText(content);
    setDelimiter(guessed);
    setName(chosen.name.replace(/\.[^.]+$/, '').replace(/[^A-Za-z0-9._-]/g, '-') || 'mapping');
    setLabelColumn(header[0] ?? '');
    setKeyColumn(header[0] ?? '');
    setColumns(
      header.slice(1).map((column) => ({ column, predicate: '', kind: 'literal' as const })),
    );
  };

  const mapping = (): CsvMapping => ({
    name,
    label_column: labelColumn,
    key_column: keyColumn || null,
    types: type ? [type] : [],
    columns: columns.filter((column) => column.predicate),
    delimiter,
  });

  const act = async (action: () => Promise<string>) => {
    setBusy(true);
    setError(null);
    try {
      setNote(await action());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const classOptions = flattenTerms(ontology.classes);

  return (
    <Dialog title="表データを取り込む" onClose={onClose} wide>
      <div className="space-y-4">
        <label className="block">
          <span className="text-sm font-medium">CSV / TSV ファイル</span>
          <input
            type="file"
            accept=".csv,.tsv,text/csv,text/tab-separated-values"
            onChange={(event) => void onFile(event.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm"
          />
        </label>

        {table.header.length > 0 && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <label className="block">
                <span className="text-xs font-medium">名前になる列</span>
                <select
                  value={labelColumn}
                  onChange={(event) => setLabelColumn(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  {table.header.map((column) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium">識別子になる列</span>
                <select
                  value={keyColumn}
                  onChange={(event) => setKeyColumn(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  <option value="">（なし）</option>
                  {table.header.map((column) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-xs font-medium">{terms.class}</span>
                <select
                  value={type}
                  onChange={(event) => setType(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  <option value="">（指定しない）</option>
                  {classOptions.map((entry) => (
                    <option key={entry.iri} value={entry.iri}>
                      {entry.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-2 py-1">列</th>
                  <th className="px-2 py-1">{terms.property}</th>
                  <th className="px-2 py-1">種別</th>
                  <th className="px-2 py-1">例</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((column, index) => (
                  <tr key={column.column}>
                    <td className="px-2 py-1 font-medium">{column.column}</td>
                    <td className="px-2 py-1">
                      <select
                        aria-label={`${column.column} の対応先`}
                        value={column.predicate}
                        onChange={(event) =>
                          setColumns((current) =>
                            current.map((entry, position) =>
                              position === index
                                ? { ...entry, predicate: event.target.value }
                                : entry,
                            ),
                          )
                        }
                        className="w-full rounded-md border border-slate-300 px-1 py-1 dark:border-slate-600 dark:bg-slate-800"
                      >
                        <option value="">（取り込まない）</option>
                        {ontology.properties.map((property) => (
                          <option key={property.iri} value={property.iri}>
                            {property.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-2 py-1">
                      <select
                        aria-label={`${column.column} の種別`}
                        value={column.kind}
                        onChange={(event) =>
                          setColumns((current) =>
                            current.map((entry, position) =>
                              position === index
                                ? { ...entry, kind: event.target.value as ColumnMapping['kind'] }
                                : entry,
                            ),
                          )
                        }
                        className="rounded-md border border-slate-300 px-1 py-1 dark:border-slate-600 dark:bg-slate-800"
                      >
                        <option value="literal">値</option>
                        <option value="reference">ほかの{terms.instance}</option>
                      </select>
                    </td>
                    <td className="px-2 py-1 text-slate-500">
                      {table.rows[0]?.[table.header.indexOf(column.column)] ?? ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        <ErrorNote message={error} />
        {note && <p className="text-xs text-slate-600 dark:text-slate-300">{note}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md px-3 py-2 text-sm">
            閉じる
          </button>
          <button
            type="button"
            disabled={busy || !labelColumn}
            onClick={() =>
              void act(async () => {
                await api.saveMapping(mapping());
                return 'この対応づけを保存しました。次回から選べます。';
              })
            }
            className="rounded-md border border-slate-300 px-3 py-2 text-sm disabled:opacity-40 dark:border-slate-600"
          >
            対応づけを保存
          </button>
          <button
            type="button"
            disabled={busy || !file || !labelColumn}
            onClick={() =>
              void act(async () => {
                const summary = await api.importFile(file as File, mapping());
                await refresh();
                return `${summary.rows} 行を取り込みました（${summary.quads} トリプル）。`;
              })
            }
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            取り込む
          </button>
        </div>
      </div>
    </Dialog>
  );
}
