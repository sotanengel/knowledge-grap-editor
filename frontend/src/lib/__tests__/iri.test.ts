import { describe, expect, it } from 'vitest';

import { isInstanceIri, localName, shortIri } from '../iri';
import { flattenTerms, findTerm, indentedOptions } from '../ontology';
import type { OntologyTerm } from '../../api/types';

const term = (iri: string, label: string, children: OntologyTerm[] = []): OntologyTerm => ({
  iri,
  label,
  comment: null,
  types: [],
  parents: [],
  domain: [],
  range: [],
  instanceCount: 0,
  children,
});

describe('making IRIs readable', () => {
  it('takes the tail after a hash, slash or colon', () => {
    expect(localName('https://example.org/kg/ont#worksFor')).toBe('worksFor');
    expect(localName('https://example.org/kg/id/alice')).toBe('alice');
    expect(localName('urn:ontoforge:data')).toBe('data');
  });

  it('uses a known prefix where there is one', () => {
    expect(shortIri('http://www.w3.org/2000/01/rdf-schema#label')).toBe('rdfs:label');
    expect(shortIri('https://schema.org/Person')).toBe('schema:Person');
  });

  it('falls back to the local name for an unknown namespace', () => {
    expect(shortIri('https://example.org/kg/ont#worksFor')).toBe('worksFor');
  });

  it('recognises an instance IRI this project minted', () => {
    const base = 'https://example.org/kg/';
    expect(isInstanceIri(`${base}id/01J8`, base)).toBe(true);
    expect(isInstanceIri(`${base}ont#Person`, base)).toBe(false);
  });
});

describe('flattening the class tree', () => {
  const tree = [term('a', '人物', [term('b', '社員', [term('c', '役員')])]), term('d', '組織')];

  it('walks depth first and records the depth', () => {
    expect(flattenTerms(tree)).toEqual([
      { iri: 'a', label: '人物', depth: 0 },
      { iri: 'b', label: '社員', depth: 1 },
      { iri: 'c', label: '役員', depth: 2 },
      { iri: 'd', label: '組織', depth: 0 },
    ]);
  });

  it('bakes the nesting into the option label', () => {
    expect(indentedOptions(tree).map((entry) => entry.label)).toEqual([
      '人物',
      '　社員',
      '　　役員',
      '組織',
    ]);
  });

  it('finds a term anywhere in the tree', () => {
    expect(findTerm(tree, 'c')?.label).toBe('役員');
    expect(findTerm(tree, 'nope')).toBeUndefined();
  });
});
