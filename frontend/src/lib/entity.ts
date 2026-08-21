/** Reading JSON-LD node objects without dragging a full JSON-LD processor in. */
import type { EntityDocument, JsonLdValue } from '../api/types';
import { RDFS_COMMENT, RDFS_LABEL, isPredicate } from './iri';

export function isNodeRef(value: JsonLdValue): value is { '@id': string } {
  return '@id' in value;
}

export function isLiteral(
  value: JsonLdValue,
): value is { '@value': string; '@type'?: string; '@language'?: string } {
  return '@value' in value;
}

/** Every value asserted for `predicate`, normalised to an array. */
export function valuesOf(document: EntityDocument, predicate: string): JsonLdValue[] {
  const raw = document[predicate];
  if (raw === undefined || raw === null) return [];
  return (Array.isArray(raw) ? raw : [raw]) as JsonLdValue[];
}

/** The display name of a node: its label, or the tail of its IRI. */
export function labelOf(document: EntityDocument, fallback = ''): string {
  const [first] = valuesOf(document, RDFS_LABEL);
  if (first && isLiteral(first)) return first['@value'];
  return fallback;
}

export function commentOf(document: EntityDocument): string {
  const [first] = valuesOf(document, RDFS_COMMENT);
  return first && isLiteral(first) ? first['@value'] : '';
}

/** The label carried alongside a node reference, when the API attached one (§9.5). */
export function referencedLabel(value: JsonLdValue): string | null {
  if (!isNodeRef(value)) return null;
  const nested = (value as Record<string, unknown>)[RDFS_LABEL];
  const [first] = (Array.isArray(nested) ? nested : nested ? [nested] : []) as JsonLdValue[];
  return first && isLiteral(first) ? first['@value'] : null;
}

export interface Attribute {
  predicate: string;
  value: string;
  datatype?: string;
  language?: string;
}

export interface Relation {
  predicate: string;
  target: string;
  targetLabel: string | null;
}

/** Split a node's predicates into literal attributes and node relations. */
export function partition(document: EntityDocument): {
  attributes: Attribute[];
  relations: Relation[];
} {
  const attributes: Attribute[] = [];
  const relations: Relation[] = [];

  for (const predicate of Object.keys(document).filter(isPredicate)) {
    if (predicate === RDFS_LABEL || predicate === RDFS_COMMENT) continue;
    for (const value of valuesOf(document, predicate)) {
      if (isLiteral(value)) {
        attributes.push({
          predicate,
          value: value['@value'],
          datatype: value['@type'],
          language: value['@language'],
        });
      } else if (isNodeRef(value)) {
        relations.push({
          predicate,
          target: value['@id'],
          targetLabel: referencedLabel(value),
        });
      }
    }
  }
  return { attributes, relations };
}

/** The value object to send back for an attribute the user edited. */
export function toLiteralValue(attribute: Attribute): JsonLdValue {
  if (attribute.language) return { '@value': attribute.value, '@language': attribute.language };
  if (attribute.datatype) return { '@value': attribute.value, '@type': attribute.datatype };
  return { '@value': attribute.value };
}

export function typesOf(document: EntityDocument): string[] {
  return document['@type'] ?? [];
}
