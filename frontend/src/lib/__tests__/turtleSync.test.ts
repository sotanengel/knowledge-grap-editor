import { describe, expect, it } from 'vitest';

import { buildUpdate, extractPrefixes, parseErrorLine } from '../turtleSync';

const TURTLE = `@prefix ex: <https://example.org/kg/id/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:alice rdfs:label "田中太郎"@ja .`;

describe('pushing the Turtle view back into the graph', () => {
  it('lifts prefix declarations above the update', () => {
    expect(extractPrefixes(TURTLE)).toBe(
      'PREFIX ex: <https://example.org/kg/id/>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>',
    );
  });

  it('replaces the data graph in one operation, so it is one undo step', () => {
    const update = buildUpdate(TURTLE);
    expect(update).toContain('DROP SILENT GRAPH <urn:ontoforge:data>');
    expect(update).toContain('INSERT DATA');
    expect(update.indexOf('PREFIX ex:')).toBeLessThan(update.indexOf('DROP SILENT'));
  });

  it('does not leave prefix lines inside the data block', () => {
    const [, body] = buildUpdate(TURTLE).split('INSERT DATA');
    expect(body).not.toContain('@prefix');
  });

  it('keeps the triples', () => {
    expect(buildUpdate(TURTLE)).toContain('ex:alice rdfs:label "田中太郎"@ja .');
  });

  it('works with no prefixes at all', () => {
    const update = buildUpdate('<https://a> <https://b> <https://c> .');
    expect(update.startsWith('DROP SILENT')).toBe(true);
  });

  it('picks the line number out of a parse error, so the editor can point at it', () => {
    expect(parseErrorLine('could not parse: Parser error at line 4 between columns 1 and 3')).toBe(
      4,
    );
    expect(parseErrorLine('invalid update: something went wrong')).toBeNull();
    expect(parseErrorLine('line 0 is not a line')).toBeNull();
  });
});
