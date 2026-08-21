/**
 * Everyday words in front, jargon behind a switch (§7.3-2).
 *
 * The default vocabulary is the one a non-engineer already has: a class is a
 * "kind", an instance is an "item", a property is a "relation" or an
 * "attribute". Anyone who prefers the RDF terms can turn them on in settings.
 */
export type Terminology = 'plain' | 'technical';

export interface TermSet {
  class: string;
  classes: string;
  instance: string;
  instances: string;
  property: string;
  properties: string;
  relation: string;
  relations: string;
  attribute: string;
  attributes: string;
  subclassOf: string;
  domain: string;
  range: string;
  ontology: string;
  inferred: string;
  vocabulary: string;
}

const PLAIN: TermSet = {
  class: '種類',
  classes: '種類',
  instance: '項目',
  instances: '項目',
  property: '関係・属性',
  properties: '関係・属性',
  relation: '関係',
  relations: '関係',
  attribute: '属性',
  attributes: '属性',
  subclassOf: '親の種類',
  domain: '主語の種類',
  range: '相手の種類',
  ontology: '語彙',
  inferred: '自動で導かれたもの',
  vocabulary: '外部語彙',
};

const TECHNICAL: TermSet = {
  class: 'クラス',
  classes: 'クラス',
  instance: 'インスタンス',
  instances: 'インスタンス',
  property: 'プロパティ',
  properties: 'プロパティ',
  relation: 'オブジェクトプロパティ',
  relations: 'オブジェクトプロパティ',
  attribute: 'データタイププロパティ',
  attributes: 'データタイププロパティ',
  subclassOf: 'rdfs:subClassOf',
  domain: 'rdfs:domain',
  range: 'rdfs:range',
  ontology: 'オントロジー (TBox)',
  inferred: '推論トリプル',
  vocabulary: '外部オントロジー',
};

export const TERM_SETS: Record<Terminology, TermSet> = {
  plain: PLAIN,
  technical: TECHNICAL,
};

export function termsFor(mode: Terminology): TermSet {
  return TERM_SETS[mode];
}
