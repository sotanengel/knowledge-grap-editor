/** Small helpers for making IRIs readable (§4.3: never make the user read one). */

const PREFIXES: Record<string, string> = {
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf',
  'http://www.w3.org/2000/01/rdf-schema#': 'rdfs',
  'http://www.w3.org/2002/07/owl#': 'owl',
  'http://www.w3.org/2001/XMLSchema#': 'xsd',
  'http://www.w3.org/2004/02/skos/core#': 'skos',
  'http://www.w3.org/ns/shacl#': 'sh',
  'http://www.w3.org/ns/prov#': 'prov',
  'http://purl.org/dc/terms/': 'dcterms',
  'http://xmlns.com/foaf/0.1/': 'foaf',
  'https://schema.org/': 'schema',
  'https://ontoforge.dev/ns#': 'ontf',
};

export const RDFS_LABEL = 'http://www.w3.org/2000/01/rdf-schema#label';
export const RDFS_COMMENT = 'http://www.w3.org/2000/01/rdf-schema#comment';
export const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';

/** The readable tail of an IRI: `…ont#worksFor` becomes `worksFor`. */
export function localName(iri: string): string {
  for (const separator of ['#', '/', ':']) {
    const index = iri.lastIndexOf(separator);
    if (index >= 0 && index < iri.length - 1) return iri.slice(index + 1);
  }
  return iri;
}

/** A prefixed name where one is known, otherwise the local name. */
export function shortIri(iri: string): string {
  for (const [namespace, prefix] of Object.entries(PREFIXES)) {
    if (iri.startsWith(namespace)) return `${prefix}:${iri.slice(namespace.length)}`;
  }
  return localName(iri);
}

/** Whether the IRI is one this instance minted for an instance node. */
export function isInstanceIri(iri: string, baseIri: string): boolean {
  return iri.startsWith(`${baseIri}id/`);
}

/** Keywords are not predicates; everything else in a node object is. */
export function isPredicate(key: string): boolean {
  return !key.startsWith('@');
}
