/**
 * The right pane (§7.1): what is known about the selected item, and the only
 * place its attributes and relations are edited (FR-04).
 */
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import { partition, labelOf, typesOf } from '../../lib/entity';
import { shortIri } from '../../lib/iri';
import { findTerm } from '../../lib/ontology';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { ErrorNote } from '../layout/ErrorNote';
import { AttributeEditor } from './AttributeEditor';
import { ProvenancePanel } from './ProvenancePanel';

export function Inspector() {
  const { selected, selectedDocument, refresh, select, validation, ontology } = useGraph();
  const { terms, showDetails } = useSettings();
  const [label, setLabel] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setLabel(selectedDocument ? labelOf(selectedDocument) : '');
    setError(null);
  }, [selectedDocument]);

  if (!selected || !selectedDocument) {
    return (
      <aside className="flex h-full w-80 shrink-0 items-center justify-center border-l border-slate-200 bg-white p-4 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900">
        {terms.instance}を選ぶと、ここに詳細が出ます。
      </aside>
    );
  }

  const { attributes, relations } = partition(selectedDocument);
  const types = typesOf(selectedDocument);
  const findings = validation?.findings.filter((finding) => finding.focusNode === selected) ?? [];

  const act = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col gap-4 overflow-y-auto border-l border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {terms.class}
        </h2>
        <p className="mt-1">
          {types.length > 0
            ? types.map((iri) => findTerm(ontology.classes, iri)?.label ?? shortIri(iri)).join(', ')
            : '（指定なし）'}
        </p>
        {showDetails && <p className="mt-1 break-all text-[10px] text-slate-400">{selected}</p>}
      </section>

      <section>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">名前</span>
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            onBlur={() => {
              const trimmed = label.trim();
              if (trimmed && trimmed !== labelOf(selectedDocument)) {
                void act(() => api.patchEntity(selected, { label: trimmed }));
              }
            }}
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 dark:border-slate-600 dark:bg-slate-800"
          />
        </label>
        <p className="mt-1 text-[10px] text-slate-400">
          名前を変えても、この{terms.instance}の識別子は変わりません。
        </p>
      </section>

      {findings.length > 0 && (
        <section className="rounded-md bg-red-50 p-3 dark:bg-red-900/30">
          <h2 className="text-xs font-semibold text-red-800 dark:text-red-200">
            検証で見つかった点
          </h2>
          <ul className="mt-1 space-y-1">
            {findings.map((finding) => (
              <li
                key={`${finding.constraint}-${finding.path}`}
                className="text-xs text-red-900 dark:text-red-100"
              >
                {finding.suggestion}
              </li>
            ))}
          </ul>
        </section>
      )}

      <AttributeEditor
        iri={selected}
        attributes={attributes}
        busy={busy}
        onChanged={() => void refresh()}
        onError={setError}
      />

      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {terms.relations}
        </h2>
        <ul className="mt-1 space-y-1">
          {relations.length === 0 && <li className="text-xs text-slate-500">まだありません。</li>}
          {relations.map((relation) => (
            <li
              key={`${relation.predicate}-${relation.target}`}
              className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <span className="text-xs text-slate-500">{shortIri(relation.predicate)}</span>
              <button
                type="button"
                onClick={() => select(relation.target)}
                className="flex-1 truncate text-left text-blue-700 hover:underline dark:text-blue-300"
              >
                {relation.targetLabel ?? shortIri(relation.target)}
              </button>
              <button
                type="button"
                aria-label="この関係を削除"
                disabled={busy}
                onClick={() =>
                  void act(() =>
                    api.patchEntity(selected, {
                      remove: { [relation.predicate]: { '@id': relation.target } },
                    }),
                  )
                }
                className="text-slate-400 hover:text-red-600"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </section>

      <ProvenancePanel iri={selected} relations={relations} />

      <ErrorNote message={error} />

      <button
        type="button"
        disabled={busy}
        onClick={() => {
          if (!window.confirm(`「${labelOf(selectedDocument)}」を削除しますか？`)) return;
          void act(async () => {
            await api.deleteEntity(selected);
            select(null);
          });
        }}
        className="mt-auto rounded-md border border-red-300 px-3 py-2 text-sm text-red-700 dark:border-red-700 dark:text-red-300"
      >
        この{terms.instance}を削除
      </button>
    </aside>
  );
}
