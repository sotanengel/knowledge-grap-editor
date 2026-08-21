/**
 * Everything the three panes read from: the loaded nodes, the vocabulary, the
 * current selection and the latest validation report.
 *
 * One place reloads, so a change made in the Turtle view shows up on the canvas
 * and in the inspector without any of them knowing about each other.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { ReactNode } from 'react';

import { api } from '../api/client';
import { subscribeToChanges } from '../api/events';
import type { EntityDocument, OntologyTree, ValidationReport } from '../api/types';
import { edgeId } from '../lib/elements';

interface GraphValue {
  entities: EntityDocument[];
  ontology: OntologyTree;
  inferredEdges: Set<string>;
  validation: ValidationReport | null;
  selected: string | null;
  selectedDocument: EntityDocument | null;
  loading: boolean;
  error: string | null;
  query: string;
  select: (iri: string | null) => void;
  setQuery: (query: string) => void;
  refresh: () => Promise<void>;
  setValidation: (report: ValidationReport | null) => void;
}

const EMPTY_ONTOLOGY: OntologyTree = { classes: [], properties: [] };
const GraphContext = createContext<GraphValue | null>(null);

const INFERRED_QUERY = `
SELECT ?s ?p ?o WHERE {
  GRAPH <urn:ontoforge:inferred> {
    ?record <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> <<( ?s ?p ?o )>>
  }
}`;

/** Which edges the reasoner produced, so the canvas can draw them dashed (§10.1). */
async function loadInferredEdges(): Promise<Set<string>> {
  try {
    const result = await api.sparql(INFERRED_QUERY);
    if (result.kind !== 'results') return new Set();
    const bindings = result.results.results?.bindings ?? [];
    const ids = bindings.flatMap((row) => {
      const { s, p, o } = row;
      if (s?.type !== 'uri' || !p || o?.type !== 'uri') return [];
      return [edgeId(s.value, p.value, o.value)];
    });
    return new Set(ids);
  } catch {
    return new Set();
  }
}

export function GraphProvider({ children }: { children: ReactNode }) {
  const [entities, setEntities] = useState<EntityDocument[]>([]);
  const [ontology, setOntology] = useState<OntologyTree>(EMPTY_ONTOLOGY);
  const [inferredEdges, setInferredEdges] = useState<Set<string>>(new Set());
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<EntityDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const latestQuery = useRef(query);
  latestQuery.current = query;

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [page, tree, inferred] = await Promise.all([
        // Only instances: the vocabulary has its own pane, and drawing class
        // definitions as nodes would confuse the two.
        api.listEntities({ q: latestQuery.current, kind: 'instance', limit: 500 }),
        api.ontology(),
        loadInferredEdges(),
      ]);
      // The search endpoint returns summaries; the canvas needs the relations,
      // so each hit is fetched in full.
      const documents = await Promise.all(
        page['@graph'].map((hit) => api.getEntity(hit['@id']).catch(() => hit as EntityDocument)),
      );
      setEntities(documents as EntityDocument[]);
      setOntology(tree);
      setInferredEdges(inferred);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, query]);

  useEffect(() => subscribeToChanges(() => void refresh()), [refresh]);

  const select = useCallback((iri: string | null) => {
    setSelected(iri);
    if (!iri) {
      setSelectedDocument(null);
      return;
    }
    api
      .getEntity(iri)
      .then((document) => setSelectedDocument(document as EntityDocument))
      .catch(() => setSelectedDocument(null));
  }, []);

  // Keep the inspector in step when the underlying node changes.
  useEffect(() => {
    if (selected) select(selected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entities]);

  const value = useMemo<GraphValue>(
    () => ({
      entities,
      ontology,
      inferredEdges,
      validation,
      selected,
      selectedDocument,
      loading,
      error,
      query,
      select,
      setQuery,
      refresh,
      setValidation,
    }),
    [
      entities,
      ontology,
      inferredEdges,
      validation,
      selected,
      selectedDocument,
      loading,
      error,
      query,
      select,
      refresh,
    ],
  );

  return <GraphContext.Provider value={value}>{children}</GraphContext.Provider>;
}

export function useGraph(): GraphValue {
  const value = useContext(GraphContext);
  if (!value) throw new Error('useGraph must be used inside a GraphProvider');
  return value;
}
