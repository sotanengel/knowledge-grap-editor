/**
 * Choosing the property for a new edge (FR-02).
 *
 * The list is narrowed by the source node's kind, because a property that
 * declares a domain only makes sense there (§7.2). Properties with no declared
 * domain always fit, so they stay on the list.
 */
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { OntologyTerm } from '../../api/types';
import { typesOf } from '../../lib/entity';
import { shortIri } from '../../lib/iri';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { Dialog } from '../layout/Dialog';
import { ErrorNote } from '../layout/ErrorNote';

interface Props {
  source: string;
  target: string;
  onClose: () => void;
  onCreated: () => void | Promise<void>;
}

export function CreateEdgeDialog({ source, target, onClose, onCreated }: Props) {
  const { entities, ontology } = useGraph();
  const { terms, showDetails } = useSettings();
  const [candidates, setCandidates] = useState<OntologyTerm[]>([]);
  const [predicate, setPredicate] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sourceDocument = entities.find((entity) => entity['@id'] === source);
  const targetDocument = entities.find((entity) => entity['@id'] === target);
  const sourceType = sourceDocument ? typesOf(sourceDocument)[0] : undefined;

  useEffect(() => {
    api
      .candidateProperties(sourceType)
      .then((result) => {
        setCandidates(result.properties);
        setPredicate(result.properties[0]?.iri ?? '');
      })
      .catch(() => setCandidates(ontology.properties));
  }, [sourceType, ontology.properties]);

  const chosen = candidates.find((entry) => entry.iri === predicate);
  const targetTypes = targetDocument ? typesOf(targetDocument) : [];
  // §7.3-3: say what is wrong *and* what would fix it.
  const rangeWarning =
    chosen && chosen.range.length > 0 && !chosen.range.some((iri) => targetTypes.includes(iri))
      ? `この${terms.relation}の相手は「${chosen.range.map(shortIri).join(' / ')}」である必要があります。` +
        `相手の${terms.class}を変えるか、別の${terms.relation}を選んでください。`
      : null;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!predicate) return;
    setBusy(true);
    setError(null);
    try {
      await api.patchEntity(source, { add: { [predicate]: { '@id': target } } });
      await onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog title={`${terms.relation}を選ぶ`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          <strong>{sourceDocument ? labelFor(sourceDocument) : source}</strong>
          {' → '}
          <strong>{targetDocument ? labelFor(targetDocument) : target}</strong>
        </p>

        <label className="block">
          <span className="text-sm font-medium">{terms.relation}</span>
          <select
            autoFocus
            value={predicate}
            onChange={(event) => setPredicate(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          >
            {candidates.length === 0 && <option value="">（定義がありません）</option>}
            {candidates.map((entry) => (
              <option key={entry.iri} value={entry.iri}>
                {entry.label}
                {showDetails ? ` — ${shortIri(entry.iri)}` : ''}
              </option>
            ))}
          </select>
        </label>

        {rangeWarning && (
          <p
            role="alert"
            className="rounded-md bg-amber-100 px-3 py-2 text-xs text-amber-900 dark:bg-amber-900/40 dark:text-amber-100"
          >
            {rangeWarning}
          </p>
        )}

        <ErrorNote message={error} />

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md px-3 py-2 text-sm">
            やめる
          </button>
          <button
            type="submit"
            disabled={busy || !predicate}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            つなぐ
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function labelFor(document: { '@id': string; [key: string]: unknown }): string {
  const label = document['http://www.w3.org/2000/01/rdf-schema#label'];
  const [first] = (Array.isArray(label) ? label : label ? [label] : []) as { '@value'?: string }[];
  return first?.['@value'] ?? document['@id'];
}
