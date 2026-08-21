/** Adding an item: type a name, pick a kind from the suggestions (§7.2). */
import { useState } from 'react';

import { api } from '../../api/client';
import { indentedOptions } from '../../lib/ontology';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { Dialog } from '../layout/Dialog';
import { ErrorNote } from '../layout/ErrorNote';

interface Props {
  /** Pre-selected when the dialog was opened by dropping a class (§7.2). */
  initialType?: string;
  onClose: () => void;
  onCreated: (iri: string) => void | Promise<void>;
}

export function CreateNodeDialog({ initialType, onClose, onCreated }: Props) {
  const { ontology } = useGraph();
  const { terms } = useSettings();
  const [label, setLabel] = useState('');
  const [type, setType] = useState(initialType ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const flatClasses = indentedOptions(ontology.classes);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!label.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createEntity({
        label: label.trim(),
        types: type ? [type] : [],
      });
      await onCreated(created['@id']);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog title={`${terms.instance}を追加`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span className="text-sm font-medium">名前</span>
          <input
            autoFocus
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="例: 田中太郎"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium">{terms.class}</span>
          <select
            value={type}
            onChange={(event) => setType(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          >
            <option value="">（指定しない）</option>
            {flatClasses.map((entry) => (
              <option key={entry.iri} value={entry.iri}>
                {entry.label}
              </option>
            ))}
          </select>
          {flatClasses.length === 0 && (
            <span className="mt-1 block text-xs text-slate-500">
              左のパネルで{terms.class}を定義すると、ここから選べるようになります。
            </span>
          )}
        </label>

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
