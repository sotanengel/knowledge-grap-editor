const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const NETWORK_ERROR =
  "Backend に接続できません（CORS または API URL を確認してください）";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
    });
  } catch {
    throw new Error(NETWORK_ERROR);
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Node {
  id: string;
  label: string;
  type: string;
  properties: Record<string, string>;
}

export interface Edge {
  id: string;
  subject: string;
  predicate: string;
  object: string;
  properties: Record<string, string>;
}

export interface OntologyClass {
  id: string;
  label: string;
  labels?: string[];
  description: string;
  aliases: string[];
  parent_classes: string[];
  examples: string[];
}

export interface PropertyDef {
  id: string;
  label: string;
  description: string;
  domain: string[];
  range: string[];
  required: boolean;
  aliases: string[];
}

export interface Relationship {
  id: string;
  label: string;
  description: string;
  domain: string[];
  range: string[];
  inverse?: string | null;
  aliases: string[];
}

export interface OwlPropertyV2 {
  iri: string;
  id: string;
  label: string;
  description: string;
  property_type: "ObjectProperty" | "DatatypeProperty" | "AnnotationProperty";
  domain: string[];
  range: string[];
  sub_property_of: string[];
  inverse_of: string | null;
  characteristics: string[];
  editor_required: boolean;
  aliases: string[];
}

export interface OwlClassV2 {
  iri: string;
  id: string;
  label: string;
  labels?: string[];
  description: string;
  aliases: string[];
  examples: string[];
  subclass_of: Array<string | Record<string, unknown>>;
  equivalent_class: Array<Record<string, unknown>>;
  disjoint_with: Array<string | Record<string, unknown>>;
}

export interface SchemaV2Response {
  classes: OwlClassV2[];
  properties: OwlPropertyV2[];
}

export interface ConsistencyReport {
  consistent: boolean;
  inconsistencies: Array<{
    code: string;
    message: string;
    involved_iris: string[];
  }>;
}

export interface SuggestResult {
  id: string;
  label: string;
  labels?: string[];
  description: string;
  score: number;
  parent_classes?: string[];
  examples?: string[];
}

export interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

export interface NeighborResult {
  center: Node;
  nodes: Node[];
  edges: Edge[];
  depth: number;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  listNodes: (type?: string) =>
    request<Node[]>(type ? `/api/nodes?type=${encodeURIComponent(type)}` : "/api/nodes"),
  getNode: (id: string) => request<Node>(`/api/nodes/${id}`),
  createNode: (data: Omit<Node, "properties"> & { properties?: Record<string, string> }) =>
    request<Node>("/api/nodes", { method: "POST", body: JSON.stringify(data) }),
  updateNode: (id: string, data: Partial<Node>) =>
    request<Node>(`/api/nodes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteNode: (id: string) => request<void>(`/api/nodes/${id}`, { method: "DELETE" }),
  listEdges: () => request<Edge[]>("/api/edges"),
  createEdge: (data: Edge) =>
    request<Edge>("/api/edges", { method: "POST", body: JSON.stringify(data) }),
  updateEdge: (id: string, data: Partial<Edge>) =>
    request<Edge>(`/api/edges/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteEdge: (id: string) => request<void>(`/api/edges/${id}`, { method: "DELETE" }),
  searchGraph: (q: string) =>
    request<GraphData>(`/api/graph/search?q=${encodeURIComponent(q)}`),
  getNeighbors: (id: string, depth = 1) =>
    request<NeighborResult>(`/api/nodes/${id}/neighbors?depth=${depth}`),
  listClasses: () => request<OntologyClass[]>("/api/ontology/classes"),
  getClassProperties: (classId: string) =>
    request<PropertyDef[]>(`/api/ontology/classes/${encodeURIComponent(classId)}/properties`),
  createClass: (data: OntologyClass & { force?: boolean }) =>
    request<OntologyClass>("/api/ontology/classes", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteClass: (id: string) =>
    request<void>(`/api/ontology/classes/${id}`, { method: "DELETE" }),
  listRelationships: () => request<Relationship[]>("/api/ontology/relationships"),
  getSchemaV2: () => request<SchemaV2Response>("/api/ontology/v2/schema"),
  listPropertiesV2: () => request<OwlPropertyV2[]>("/api/ontology/v2/properties"),
  getConsistency: () => request<ConsistencyReport>("/api/ontology/v2/consistency"),
  createRelationship: (data: Relationship) =>
    request<Relationship>("/api/ontology/relationships", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  suggestTypes: (q: string) =>
    request<{ results: SuggestResult[] }>(`/api/ontology/suggest?q=${encodeURIComponent(q)}`),
  suggestRelationships: (q: string) =>
    request<{ results: SuggestResult[] }>(
      `/api/ontology/suggest/relationships?q=${encodeURIComponent(q)}`,
    ),
  exportRdf: (format: string) =>
    fetch(`${API_URL}/api/export?format=${format}`).then((r) => r.blob()),
};
