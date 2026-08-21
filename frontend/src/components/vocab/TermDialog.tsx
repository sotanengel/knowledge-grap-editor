/** Defining a class or a property from a form, never from typed Turtle (FR-03). */
import { useState } from 'react';

import { api } from '../../api/client';
import { indentedOptions } from '../../lib/ontology';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { Dialog } from '../layout/Dialog';
import { ErrorNote } from '../layout/ErrorNote';

interface Props {
  kind: 'class' | 'property';
  onClose: () => void;
  onCreated: () => void | Promise<void>;
}

export function TermDialog({ kind, onClose, onCreated }: Props) {
  const { ontology } = useGraph();
  const { terms } = useSettings();
  const [label, setLabel] = useState('');
  const [parent, setParent] = useState('');
  const [domain, setDomain] = useState('');
  const [range, setRange] = useState('');
  const [valueKind, setValueKind] = useState<'object' | 'datatype'>('object');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const classOptions = indentedOptions(ontology.classes);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!label.trim()) return;
    setBusy(true);
    setError(null);
    try {
      if (kind === 'class') {
        await api.createClass({ label: label.trim(), parents: parent ? [parent] : [] });
      } else {
        await api.createProperty({
          label: label.trim(),
          kind: valueKind,
          domain: domain || undefined,
          range: valueKind === 'object' ? range || undefined : undefined,
        });
      }
      await onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      title={kind === 'class' ? `${terms.class}を追加` : `${terms.property}を追加`}
      onClose={onClose}
    >
      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span className="text-sm font-medium">名前</span>
          <input
            autoFocus
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder={kind === 'class' ? '例: 人物' : '例: 所属'}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
        </label>

        {kind === 'class' ? (
          <label className="block">
            <span className="text-sm font-medium">{terms.subclassOf}</span>
            <select
              value={parent}
              onChange={(event) => setParent(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
            >
              <option value="">（なし）</option>
              {classOptions.map((entry) => (
                <option key={entry.iri} value={entry.iri}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <>
            <fieldset>
              <legend className="text-sm font-medium">つなぐ相手</legend>
              <label className="mr-4 text-sm">
                <input
                  type="radio"
                  checked={valueKind === 'object'}
                  onChange={() => setValueKind('object')}
                />{' '}
                ほかの{terms.instance}（{terms.relation}）
              </label>
              <label className="text-sm">
                <input
                  type="radio"
                  checked={valueKind === 'datatype'}
                  onChange={() => setValueKind('datatype')}
                />{' '}
                値（{terms.attribute}）
              </label>
            </fieldset>

            <label className="block">
              <span className="text-sm font-medium">{terms.domain}</span>
              <select
                value={domain}
                onChange={(event) => setDomain(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
              >
                <option value="">（指定しない）</option>
                {classOptions.map((entry) => (
                  <option key={entry.iri} value={entry.iri}>
                    {entry.label}
                  </option>
                ))}
              </select>
            </label>

            {valueKind === 'object' && (
              <label className="block">
                <span className="text-sm font-medium">{terms.range}</span>
                <select
                  value={range}
                  onChange={(event) => setRange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                >
                  <option value="">（指定しない）</option>
                  {classOptions.map((entry) => (
                    <option key={entry.iri} value={entry.iri}>
                      {entry.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        )}

        <ErrorNote message={error} />

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md px-3 py-2 text-sm">
            やめる
          </button>
          <button
            type="submit"
            disabled={busy || !label.trim()}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            追加
          </button>
        </div>
      </form>
    </Dialog>
  );
}
