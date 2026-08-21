/**
 * Where an edge came from, and how confident we are (§6.3, §7.1).
 *
 * The metadata is stored on an RDF 1.2 reifier, but nothing about that surfaces
 * here: the user sees a source URL and a confidence slider.
 */
import { useState } from 'react';

import { api } from '../../api/client';
import type { Relation } from '../../lib/entity';
import { shortIri } from '../../lib/iri';
import { useSettings } from '../../state/settings';

const PROV_DERIVED = 'http://www.w3.org/ns/prov#wasDerivedFrom';
const ONTF_CONFIDENCE = 'https://ontoforge.dev/ns#confidence';

interface Props {
  iri: string;
  relations: Relation[];
}

export function ProvenancePanel({ iri, relations }: Props) {
  const { showDetails } = useSettings();
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState('');
  const [confidence, setConfidence] = useState(1);
  const [target, setTarget] = useState('');
  const [note, setNote] = useState<string | null>(null);

  // Provenance is a detail: it stays folded away until asked for (§7.3-1).
  if (!showDetails || relations.length === 0) return null;

  const chosen = relations.find(
    (relation) => `${relation.predicate}|${relation.target}` === target,
  );

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!chosen) return;
    try {
      await api.sparqlUpdate(buildUpdate(iri, chosen, source, confidence));
      setNote('出典を記録しました。');
    } catch (cause) {
      setNote(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <section>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        className="text-xs font-semibold uppercase tracking-wide text-slate-500"
      >
        {open ? '▾' : '▸'} 出典・確信度
      </button>

      {open && (
        <form onSubmit={save} className="mt-2 space-y-2">
          <select
            aria-label="対象の関係"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
            className="w-full rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-800"
          >
            <option value="">関係を選ぶ…</option>
            {relations.map((relation) => (
              <option
                key={`${relation.predicate}|${relation.target}`}
                value={`${relation.predicate}|${relation.target}`}
              >
                {shortIri(relation.predicate)} → {relation.targetLabel ?? shortIri(relation.target)}
              </option>
            ))}
          </select>

          <input
            value={source}
            onChange={(event) => setSource(event.target.value)}
            placeholder="出典 URL"
            className="w-full rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-800"
          />

          <label className="block text-xs">
            確信度: {confidence.toFixed(2)}
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={confidence}
              onChange={(event) => setConfidence(Number(event.target.value))}
              className="w-full"
            />
          </label>

          <button
            type="submit"
            disabled={!chosen || !source}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs disabled:opacity-40 dark:border-slate-600"
          >
            記録する
          </button>
          {note && <p className="text-[10px] text-slate-500">{note}</p>}
        </form>
      )}
    </section>
  );
}

/** The RDF 1.2 reifier, written as a SPARQL Update the UI session is allowed to run. */
function buildUpdate(iri: string, relation: Relation, source: string, confidence: number): string {
  const statement = `<<( <${iri}> <${relation.predicate}> <${relation.target}> )>>`;
  return `
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX ontf: <https://ontoforge.dev/ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {
  GRAPH <urn:ontoforge:data> {
    _:statement rdf:reifies ${statement} ;
      <${PROV_DERIVED}> <${source}> ;
      <${ONTF_CONFIDENCE}> "${confidence}"^^xsd:decimal .
  }
}`.trim();
}
