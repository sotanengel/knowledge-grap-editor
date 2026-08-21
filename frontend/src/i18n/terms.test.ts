import { describe, expect, it } from 'vitest';

import { TERM_SETS, termsFor } from './terms';

describe('terminology', () => {
  it('speaks plainly by default', () => {
    const terms = termsFor('plain');
    expect(terms.class).toBe('種類');
    expect(terms.instance).toBe('項目');
    expect(terms.property).toBe('関係・属性');
  });

  it('switches to RDF vocabulary on request', () => {
    const terms = termsFor('technical');
    expect(terms.class).toBe('クラス');
    expect(terms.instance).toBe('インスタンス');
  });

  it('defines every term in both modes', () => {
    const keys = Object.keys(TERM_SETS.plain);
    expect(Object.keys(TERM_SETS.technical)).toEqual(keys);
    for (const set of Object.values(TERM_SETS)) {
      expect(Object.values(set).every((value) => value.length > 0)).toBe(true);
    }
  });
});
