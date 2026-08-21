import { describe, expect, it } from 'vitest';

import { guessDelimiter, parseDelimited, preview } from '../csv';

describe('reading a delimited file for the mapping preview', () => {
  it('splits rows and fields', () => {
    expect(parseDelimited('a,b\n1,2\n')).toEqual([
      ['a', 'b'],
      ['1', '2'],
    ]);
  });

  it('keeps a delimiter that sits inside quotes', () => {
    expect(parseDelimited('a,b\n"x,y",2\n')[1]).toEqual(['x,y', '2']);
  });

  it('understands a doubled quote as a literal one', () => {
    expect(parseDelimited('a\n"he said ""hi"""\n')[1]).toEqual(['he said "hi"']);
  });

  it('keeps a newline inside a quoted field', () => {
    expect(parseDelimited('a,b\n"one\ntwo",2\n')[1]).toEqual(['one\ntwo', '2']);
  });

  it('handles tab-separated input', () => {
    expect(parseDelimited('a\tb\n1\t2\n', '\t')[1]).toEqual(['1', '2']);
  });

  it('guesses the delimiter from the header', () => {
    expect(guessDelimiter('a\tb\tc\n')).toBe('\t');
    expect(guessDelimiter('a,b,c\n')).toBe(',');
  });

  it('previews only the first few rows', () => {
    const text = ['key,name', ...Array.from({ length: 20 }, (_, n) => `${n},row${n}`)].join('\n');
    const result = preview(text, ',', 3);
    expect(result.header).toEqual(['key', 'name']);
    expect(result.rows).toHaveLength(3);
  });

  it('copes with an empty file', () => {
    expect(preview('')).toEqual({ header: [], rows: [] });
  });
});
