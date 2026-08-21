/**
 * Literal attributes, with the type the system guessed shown as a dropdown the
 * user can correct (FR-04, §4.3). Nobody types `^^xsd:date`.
 */
import { useState } from 'react';

import { api } from '../../api/client';
import { DATATYPES, selectedDatatype } from '../../lib/datatypes';
import type { Attribute } from '../../lib/entity';
import { shortIri } from '../../lib/iri';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';

interface Props {
  iri: string;
  attributes: Attribute[];
  busy: boolean;
  onChanged: () => void;
  onError: (message: string | null) => void;
}

export function AttributeEditor({ iri, attributes, busy, onChanged, onError }: Props) {
  const { ontology } = useGraph();
  const { terms } = useSettings();
  const [newPredicate, setNewPredicate] = useState('');
  const [newValue, setNewValue] = useState('');

  const datatypeProperties = ontology.properties.filter(
    (property) => !property.types.includes('http://www.w3.org/2002/07/owl#ObjectProperty'),
  );

  const change = async (action: () => Promise<unknown>) => {
    onError(null);
    try {
      await action();
      onChanged();
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <section>
      <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {terms.attributes}
      </h2>

      <ul className="mt-1 space-y-2">
        {attributes.length === 0 && <li className="text-xs text-slate-500">まだありません。</li>}
        {attributes.map((attribute) => (
          <li key={`${attribute.predicate}-${attribute.value}`} className="space-y-1">
            <div className="flex items-center gap-1">
              <span className="flex-1 text-xs text-slate-500">{shortIri(attribute.predicate)}</span>
              <button
                type="button"
                aria-label="この属性を削除"
                disabled={busy}
                onClick={() =>
                  void change(() =>
                    api.patchEntity(iri, {
                      remove: {
                        [attribute.predicate]: attribute.language
                          ? { '@value': attribute.value, '@language': attribute.language }
                          : { '@value': attribute.value, '@type': attribute.datatype },
                      },
                    }),
                  )
                }
                className="text-slate-400 hover:text-red-600"
              >
                ×
              </button>
            </div>
            <div className="flex gap-1">
              <input
                defaultValue={attribute.value}
                disabled={busy}
                onBlur={(event) => {
                  const next = event.target.value;
                  if (next === attribute.value) return;
                  void change(() =>
                    api.patchEntity(iri, {
                      remove: {
                        [attribute.predicate]: attribute.language
                          ? { '@value': attribute.value, '@language': attribute.language }
                          : { '@value': attribute.value, '@type': attribute.datatype },
                      },
                      add: {
                        [attribute.predicate]: attribute.language
                          ? { '@value': next, '@language': attribute.language }
                          : { '@value': next, '@type': attribute.datatype },
                      },
                    }),
                  );
                }}
                className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
              />
              <select
                aria-label="型"
                value={selectedDatatype(attribute.datatype, attribute.language)}
                disabled={busy}
                onChange={(event) => {
                  const datatype = event.target.value;
                  void change(() =>
                    api.patchEntity(iri, {
                      remove: {
                        [attribute.predicate]: attribute.language
                          ? { '@value': attribute.value, '@language': attribute.language }
                          : { '@value': attribute.value, '@type': attribute.datatype },
                      },
                      add: {
                        [attribute.predicate]:
                          datatype === 'lang'
                            ? { '@value': attribute.value, '@language': 'ja' }
                            : { '@value': attribute.value, '@type': datatype },
                      },
                    }),
                  );
                }}
                className="w-24 rounded-md border border-slate-300 px-1 py-1 text-xs dark:border-slate-600 dark:bg-slate-800"
              >
                {DATATYPES.map((entry) => (
                  <option key={entry.value} value={entry.value}>
                    {entry.label}
                  </option>
                ))}
                <option value="lang">日本語文</option>
              </select>
            </div>
          </li>
        ))}
      </ul>

      <form
        className="mt-2 flex gap-1"
        onSubmit={(event) => {
          event.preventDefault();
          if (!newPredicate || !newValue.trim()) return;
          void change(async () => {
            await api.patchEntity(iri, { add: { [newPredicate]: newValue.trim() } });
            setNewValue('');
          });
        }}
      >
        <select
          aria-label={`${terms.attribute}を選ぶ`}
          value={newPredicate}
          onChange={(event) => setNewPredicate(event.target.value)}
          className="w-28 rounded-md border border-slate-300 px-1 py-1 text-xs dark:border-slate-600 dark:bg-slate-800"
        >
          <option value="">選ぶ…</option>
          {datatypeProperties.map((property) => (
            <option key={property.iri} value={property.iri}>
              {property.label}
            </option>
          ))}
        </select>
        <input
          value={newValue}
          onChange={(event) => setNewValue(event.target.value)}
          placeholder="値"
          className="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
        <button
          type="submit"
          disabled={busy || !newPredicate || !newValue.trim()}
          className="rounded-md border border-slate-300 px-2 text-sm disabled:opacity-40 dark:border-slate-600"
        >
          ＋
        </button>
      </form>
      <p className="mt-1 text-[10px] text-slate-400">
        型は値から推定します。必要なら変更できます。
      </p>
    </section>
  );
}
