/** Flattening the class tree for the dropdowns that need a flat list. */
import type { OntologyTerm } from '../api/types';

export interface FlatTerm {
  iri: string;
  label: string;
  depth: number;
}

/** Depth-first walk, keeping the nesting visible through an indent. */
export function flattenTerms(terms: OntologyTerm[], depth = 0): FlatTerm[] {
  return terms.flatMap((term) => [
    { iri: term.iri, label: term.label, depth },
    ...flattenTerms(term.children, depth + 1),
  ]);
}

/** The same list with the indent baked into the label, for `<option>` text. */
export function indentedOptions(terms: OntologyTerm[]): { iri: string; label: string }[] {
  return flattenTerms(terms).map((term) => ({
    iri: term.iri,
    label: `${'　'.repeat(term.depth)}${term.label}`,
  }));
}

export function findTerm(terms: OntologyTerm[], iri: string): FlatTerm | undefined {
  return flattenTerms(terms).find((term) => term.iri === iri);
}
