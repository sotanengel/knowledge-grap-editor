/**
 * The typed HTTP client.
 *
 * Everything the UI does goes through here, so error handling and the optional
 * bearer token live in exactly one place.
 */
import type {
  CsvMapping,
  GitStatus,
  EntityDocument,
  EntityPage,
  Explanation,
  GraphDocument,
  Health,
  HistoryPage,
  ImportSummary,
  OntologyTree,
  ProjectList,
  ProjectSummary,
  ReasonSummary,
  ReasonerProfiles,
  SemanticHit,
  SemanticStatus,
  SparqlResults,
  ValidationReport,
  VocabularyCatalogue,
} from './types';

export const API = '/api/v1';

/** A request the server refused, carrying enough to show the user why. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

let authToken: string | null = null;

/** Set once at startup when the instance is behind `ONTOFORGE_AUTH_TOKEN` (§13). */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

function headers(extra: Record<string, string> = {}): Record<string, string> {
  return authToken ? { ...extra, Authorization: `Bearer ${authToken}` } : extra;
}

async function readError(response: Response): Promise<never> {
  let detail = response.statusText;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') {
      detail = body.detail;
    } else if (body.detail) {
      detail = JSON.stringify(body.detail);
    }
  } catch {
    // A non-JSON error body is fine; the status text still says something.
  }
  throw new ApiError(response.status, detail);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { ...init, headers: headers(init.headers as never) });
  if (!response.ok) return readError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function json<T>(path: string, method: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function text(path: string, init: RequestInit = {}): Promise<string> {
  const response = await fetch(path, { ...init, headers: headers(init.headers as never) });
  if (!response.ok) return readError(response);
  return response.text();
}

export interface CreateEntityBody {
  label: string;
  types?: string[];
  properties?: Record<string, unknown>;
  comment?: string;
  language?: string;
}

export interface PatchEntityBody {
  add?: Record<string, unknown>;
  remove?: Record<string, unknown>;
  label?: string;
  comment?: string;
}

export const api = {
  health: () => request<Health>(`${API}/health`),

  // ---------------------------------------------------------------- entities

  listEntities: (
    params: {
      q?: string;
      type?: string;
      kind?: 'instance' | 'term';
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.type) query.set('type', params.type);
    if (params.kind) query.set('kind', params.kind);
    query.set('limit', String(params.limit ?? 200));
    query.set('offset', String(params.offset ?? 0));
    return request<EntityPage>(`${API}/entities?${query}`);
  },

  getEntity: (iri: string, depth = 1) =>
    request<EntityDocument | GraphDocument>(
      `${API}/entities/${encodeURIComponent(iri)}?depth=${depth}`,
    ),

  createEntity: (body: CreateEntityBody) => json<EntityDocument>(`${API}/entities`, 'POST', body),

  patchEntity: (iri: string, body: PatchEntityBody) =>
    json<EntityDocument>(`${API}/entities/${encodeURIComponent(iri)}`, 'PATCH', body),

  deleteEntity: (iri: string) =>
    request<{ removed: number }>(`${API}/entities/${encodeURIComponent(iri)}`, {
      method: 'DELETE',
    }),

  // ---------------------------------------------------------------- ontology

  ontology: () => request<OntologyTree>(`${API}/ontology`),

  candidateProperties: (domain?: string) =>
    request<{ properties: OntologyTree['properties'] }>(
      `${API}/ontology/properties${domain ? `?domain=${encodeURIComponent(domain)}` : ''}`,
    ),

  createClass: (body: { label: string; parents?: string[]; comment?: string }) =>
    json<EntityDocument>(`${API}/ontology/classes`, 'POST', body),

  createProperty: (body: {
    label: string;
    kind?: 'object' | 'datatype';
    parents?: string[];
    domain?: string;
    range?: string;
    comment?: string;
  }) => json<EntityDocument>(`${API}/ontology/properties`, 'POST', body),

  renameTerm: (iri: string, label: string) =>
    json<EntityDocument>(`${API}/ontology/rename`, 'POST', { iri, label }),

  // ---------------------------------------------------------------- sparql

  sparql: (query: string) =>
    fetch('/sparql', {
      method: 'POST',
      headers: headers({ 'Content-Type': 'application/sparql-query' }),
      body: query,
    }).then(async (response) => {
      if (!response.ok) return readError(response);
      const contentType = response.headers.get('content-type') ?? '';
      if (contentType.includes('json')) {
        return { kind: 'results' as const, results: (await response.json()) as SparqlResults };
      }
      return { kind: 'turtle' as const, turtle: await response.text() };
    }),

  sparqlUpdate: (update: string) =>
    request<{ additions: number; deletions: number; seq: number }>('/sparql/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/sparql-update' },
      body: update,
    }),

  // ---------------------------------------------------------------- analysis

  reason: (profile?: string) =>
    json<ReasonSummary>(`${API}/reason`, 'POST', profile ? { profile } : {}),

  reasonerProfiles: () => request<ReasonerProfiles>(`${API}/reason/profiles`),

  explain: (subject: string, predicate: string, object: string) =>
    json<Explanation>(`${API}/reason/explain`, 'POST', { subject, predicate, object }),

  validate: () => json<ValidationReport>(`${API}/validate`, 'POST', {}),

  vocabularies: () => request<VocabularyCatalogue>(`${API}/vocabularies`),

  loadVocabularies: (names: string[]) =>
    json<{ loaded: Record<string, number> }>(`${API}/vocabularies`, 'POST', { names }),

  // ---------------------------------------------------------------- transfer

  exportGraph: (format: string, graphs?: string[]) =>
    text(`${API}/export?format=${format}${graphs ? `&graphs=${graphs.join(',')}` : ''}`),

  exportUrl: (format: string) => `${API}/export?format=${format}`,

  importFile: (file: File, mapping?: CsvMapping) => {
    const body = new FormData();
    body.append('file', file);
    if (mapping) body.append('mapping', JSON.stringify(mapping));
    return request<ImportSummary>(`${API}/import`, { method: 'POST', body });
  },

  listMappings: () => request<{ names: string[] }>(`${API}/mappings`),

  saveMapping: (mapping: CsvMapping) =>
    json<CsvMapping>(`${API}/mappings/${encodeURIComponent(mapping.name)}`, 'PUT', mapping),

  getMapping: (name: string) => request<CsvMapping>(`${API}/mappings/${encodeURIComponent(name)}`),

  // ---------------------------------------------------------------- projects

  projects: () => request<ProjectList>(`${API}/projects`),

  createProject: (name: string, id?: string) =>
    json<ProjectSummary>(`${API}/projects`, 'POST', { name, id }),

  switchProject: (id: string) =>
    request<{ current: string }>(`${API}/projects/${encodeURIComponent(id)}/switch`, {
      method: 'POST',
    }),

  renameProject: (id: string, name: string) =>
    json<ProjectSummary>(`${API}/projects/${encodeURIComponent(id)}`, 'PATCH', { name }),

  deleteProject: (id: string) =>
    request<{ deleted: string; current: string }>(`${API}/projects/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),

  // ---------------------------------------------------------------- semantic

  semanticStatus: () => request<SemanticStatus>(`${API}/semantic`),

  semanticSearch: (q: string, limit = 10) =>
    request<{ results: SemanticHit[] }>(
      `${API}/semantic/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),

  // ---------------------------------------------------------------- git

  gitStatus: () => request<GitStatus>(`${API}/git`),

  gitCommit: () =>
    request<{ committed: boolean; revision: string | null; files: number }>(`${API}/git/commit`, {
      method: 'POST',
    }),

  // ---------------------------------------------------------------- history

  history: (limit = 50) => request<HistoryPage>(`${API}/history?limit=${limit}`),

  undo: () => request<{ seq: number }>(`${API}/history/undo`, { method: 'POST' }),

  redo: () => request<{ seq: number }>(`${API}/history/redo`, { method: 'POST' }),
};

export type Api = typeof api;
