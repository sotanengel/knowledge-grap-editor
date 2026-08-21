/** Shapes returned by the OntoForge API (§8). */

/** A JSON-LD value object: either a node reference or a literal. */
export type JsonLdValue =
  | { '@id': string; [predicate: string]: unknown }
  | { '@value': string; '@type'?: string; '@language'?: string };

/** A JSON-LD node object, with arbitrary predicates alongside the keywords. */
export interface EntityDocument {
  '@context'?: Record<string, string>;
  '@id': string;
  '@type'?: string[];
  [predicate: string]: unknown;
}

export interface GraphDocument {
  '@context': Record<string, string>;
  '@id'?: string;
  '@graph': EntityDocument[];
}

export interface EntityPage extends GraphDocument {
  limit: number;
  offset: number;
}

export interface OntologyTerm {
  iri: string;
  label: string;
  comment: string | null;
  types: string[];
  parents: string[];
  domain: string[];
  range: string[];
  instanceCount: number;
  children: OntologyTerm[];
}

export interface OntologyTree {
  classes: OntologyTerm[];
  properties: OntologyTerm[];
}

export interface HistoryEntry {
  seq: number;
  id: string;
  actor: string;
  timestamp: string;
  additions: number;
  deletions: number;
  inverse_of: string | null;
}

export interface HistoryPage {
  entries: HistoryEntry[];
  can_undo: boolean;
  can_redo: boolean;
}

export interface ReasonSummary {
  profile: string;
  derived: number;
  iterations: number;
  reachedFixedPoint: boolean;
  hitDerivationCap: boolean;
}

export interface ReasonerRule {
  name: string;
  description: string;
}

export interface ReasonerProfiles {
  current: string;
  profiles: { name: string; rules: ReasonerRule[] }[];
}

export interface Explanation {
  triple: { subject: string; predicate: string; object: string; text: string };
  rule: string;
  premises: { subject: string; predicate: string; object: string; text: string }[];
}

export interface ValidationFinding {
  focusNode: string;
  focusLabel: string;
  path: string | null;
  message: string;
  severity: string;
  constraint: string;
  value: string | null;
  suggestion: string;
}

export interface ValidationReport {
  conforms: boolean;
  shapes: number;
  findings: ValidationFinding[];
  violated: string[];
}

export interface SparqlBinding {
  type: 'uri' | 'literal' | 'bnode';
  value: string;
  datatype?: string;
  'xml:lang'?: string;
}

export interface SparqlResults {
  head: { vars?: string[] };
  results?: { bindings: Record<string, SparqlBinding>[] };
  boolean?: boolean;
}

export interface VocabularyEntry {
  name: string;
  title: string;
  prefix: string;
  namespace: string;
  licence: string;
}

export interface VocabularyCatalogue {
  available: VocabularyEntry[];
  loaded: string[];
  defaults: string[];
}

export interface Health {
  status: string;
  version: string;
  quads: number;
  base_iri: string;
  reasoner: string;
  auth_required: boolean;
}

export interface ChangeEvent {
  type: 'ready' | 'change' | 'undo' | 'redo';
  seq: number;
  actor?: string;
  additions?: number;
  deletions?: number;
}

export interface ColumnMapping {
  column: string;
  predicate: string;
  kind: 'literal' | 'reference';
  datatype?: string | null;
  language?: string | null;
  skip_empty?: boolean;
}

export interface CsvMapping {
  name: string;
  label_column: string;
  key_column?: string | null;
  types: string[];
  columns: ColumnMapping[];
  delimiter: string;
}

export interface ImportSummary {
  quads: number;
  rows: number;
  iris: string[];
  format: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  createdAt: string;
}

export interface ProjectList {
  current: string;
  projects: ProjectSummary[];
}

export interface SemanticStatus {
  enabled: boolean;
  indexed: number;
  note: string;
}

export interface SemanticHit {
  iri: string;
  label: string;
  score: number;
}

export interface GitStatus {
  available: boolean;
  enabled: boolean;
  initialised: boolean;
  pending: string[];
  log: { revision: string; timestamp: string; subject: string }[];
  remote: string | null;
}
