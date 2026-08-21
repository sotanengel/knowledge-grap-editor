import { describe, expect, it } from 'vitest';

import type { EntityDocument, JsonLdValue } from '../../api/types';
import { labelOf, partition, referencedLabel, typesOf, valuesOf } from '../entity';
import { RDFS_LABEL } from '../iri';

const WORKS_FOR = 'https://example.org/kg/ont#worksFor';
const BIRTH_DATE = 'https://example.org/kg/ont#birthDate';

const ALICE: EntityDocument = {
  '@id': 'https://example.org/kg/id/alice',
  '@type': ['https://example.org/kg/ont#Person'],
  [RDFS_LABEL]: [{ '@value': '田中太郎', '@language': 'ja' }],
  [BIRTH_DATE]: [{ '@value': '1990-04-01', '@type': 'http://www.w3.org/2001/XMLSchema#date' }],
  [WORKS_FOR]: [
    {
      '@id': 'https://example.org/kg/id/acme',
      [RDFS_LABEL]: [{ '@value': '株式会社アクメ', '@language': 'ja' }],
    },
  ],
};

describe('reading a JSON-LD node object', () => {
  it('finds the label', () => {
    expect(labelOf(ALICE)).toBe('田中太郎');
  });

  it('falls back when there is no label', () => {
    expect(labelOf({ '@id': 'x' }, '(名前なし)')).toBe('(名前なし)');
  });

  it('normalises a single value to an array', () => {
    expect(valuesOf({ '@id': 'x', p: { '@value': 'a' } }, 'p')).toEqual([{ '@value': 'a' }]);
    expect(valuesOf({ '@id': 'x' }, 'p')).toEqual([]);
  });

  it('reads the types', () => {
    expect(typesOf(ALICE)).toEqual(['https://example.org/kg/ont#Person']);
    expect(typesOf({ '@id': 'x' })).toEqual([]);
  });

  it('separates literal attributes from node relations', () => {
    const { attributes, relations } = partition(ALICE);
    expect(attributes).toEqual([
      {
        predicate: BIRTH_DATE,
        value: '1990-04-01',
        datatype: 'http://www.w3.org/2001/XMLSchema#date',
        language: undefined,
      },
    ]);
    expect(relations).toEqual([
      {
        predicate: WORKS_FOR,
        target: 'https://example.org/kg/id/acme',
        targetLabel: '株式会社アクメ',
      },
    ]);
  });

  it('leaves the label and comment out of the attribute list', () => {
    const predicates = partition(ALICE).attributes.map((attribute) => attribute.predicate);
    expect(predicates).not.toContain(RDFS_LABEL);
  });

  it('reads the label the API attached to a reference, so no bare IRI is shown', () => {
    const references = ALICE[WORKS_FOR] as JsonLdValue[];
    expect(references).toHaveLength(1);
    expect(referencedLabel(references[0] as JsonLdValue)).toBe('株式会社アクメ');
    expect(referencedLabel({ '@id': 'https://x' })).toBeNull();
  });
});
