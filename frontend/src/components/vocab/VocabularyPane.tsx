/**
 * The left pane (§7.1): the class hierarchy, the property list, and the
 * external vocabularies bundled with the product.
 *
 * Dragging a class onto the canvas is how a vocabulary gets reused (FR-05); the
 * canvas reads the drag payload and offers to create an item of that kind.
 */
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { OntologyTerm, VocabularyCatalogue } from '../../api/types';
import { CLASS_DRAG_TYPE } from '../../lib/dragTypes';
import { shortIri } from '../../lib/iri';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { ErrorNote } from '../layout/ErrorNote';
import { TermDialog } from './TermDialog';

type Section = 'classes' | 'properties' | 'vocabularies';

export function VocabularyPane() {
  const { ontology, refresh, setQuery } = useGraph();
  const { terms, showDetails } = useSettings();
  const [open, setOpen] = useState<Record<Section, boolean>>({
    classes: true,
    properties: true,
    vocabularies: false,
  });
  const [creating, setCreating] = useState<'class' | 'property' | null>(null);
  const [catalogue, setCatalogue] = useState<VocabularyCatalogue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingVocab, setLoadingVocab] = useState<string | null>(null);

  useEffect(() => {
    api
      .vocabularies()
      .then(setCatalogue)
      .catch(() => setCatalogue(null));
  }, []);

  const toggle = (section: Section) =>
    setOpen((current) => ({ ...current, [section]: !current[section] }));

  const loadVocabulary = async (name: string) => {
    setLoadingVocab(name);
    setError(null);
    try {
      await api.loadVocabularies([name]);
      setCatalogue(await api.vocabularies());
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoadingVocab(null);
    }
  };

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col overflow-y-auto border-r border-slate-200 bg-white text-sm dark:border-slate-800 dark:bg-slate-900">
      <SectionHeader
        title={terms.classes}
        open={open.classes}
        onToggle={() => toggle('classes')}
        onAdd={() => setCreating('class')}
        addLabel={`${terms.class}を追加`}
      />
      {open.classes && (
        <TermTree
          terms={ontology.classes}
          emptyMessage={`まだ${terms.class}がありません。`}
          showDetails={showDetails}
          onPick={(term) => setQuery(term.label)}
        />
      )}

      <SectionHeader
        title={terms.properties}
        open={open.properties}
        onToggle={() => toggle('properties')}
        onAdd={() => setCreating('property')}
        addLabel={`${terms.property}を追加`}
      />
      {open.properties && (
        <ul className="px-2 pb-2">
          {ontology.properties.length === 0 && (
            <li className="px-2 py-1 text-xs text-slate-500">まだ{terms.property}がありません。</li>
          )}
          {ontology.properties.map((property) => (
            <li key={property.iri} className="px-2 py-1">
              <span className="font-medium">{property.label}</span>
              {(property.domain.length > 0 || property.range.length > 0) && (
                <span className="ml-1 text-xs text-slate-500">
                  {property.domain.map(shortIri).join('/') || '—'} →{' '}
                  {property.range.map(shortIri).join('/') || '—'}
                </span>
              )}
              {showDetails && (
                <span className="block text-[10px] text-slate-400">{shortIri(property.iri)}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      <SectionHeader
        title={terms.vocabulary}
        open={open.vocabularies}
        onToggle={() => toggle('vocabularies')}
      />
      {open.vocabularies && (
        <ul className="px-2 pb-2">
          {catalogue?.available.map((entry) => {
            const loaded = catalogue.loaded.includes(entry.name);
            return (
              <li key={entry.name} className="flex items-center gap-2 px-2 py-1">
                <span className="flex-1">
                  {entry.title}
                  <span className="block text-[10px] text-slate-400">{entry.prefix}</span>
                </span>
                {loaded ? (
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400">読込済</span>
                ) : (
                  <button
                    type="button"
                    disabled={loadingVocab !== null}
                    onClick={() => void loadVocabulary(entry.name)}
                    className="rounded border border-slate-300 px-2 py-0.5 text-[10px] dark:border-slate-600"
                  >
                    {loadingVocab === entry.name ? '読込中' : '読み込む'}
                  </button>
                )}
              </li>
            );
          })}
          <li className="px-2 pt-2 text-[10px] text-slate-500">
            語彙はすべて同梱されています。外部への通信は行いません。
          </li>
        </ul>
      )}

      <div className="px-3 pb-3">
        <ErrorNote message={error} />
      </div>

      {creating && (
        <TermDialog
          kind={creating}
          onClose={() => setCreating(null)}
          onCreated={async () => {
            setCreating(null);
            await refresh();
          }}
        />
      )}
    </aside>
  );
}

function SectionHeader({
  title,
  open,
  onToggle,
  onAdd,
  addLabel,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  onAdd?: () => void;
  addLabel?: string;
}) {
  return (
    <div className="flex items-center gap-1 border-b border-slate-100 px-3 py-2 dark:border-slate-800">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex-1 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
      >
        {open ? '▾' : '▸'} {title}
      </button>
      {onAdd && (
        <button
          type="button"
          onClick={onAdd}
          aria-label={addLabel}
          title={addLabel}
          className="rounded px-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          ＋
        </button>
      )}
    </div>
  );
}

function TermTree({
  terms,
  emptyMessage,
  showDetails,
  onPick,
  depth = 0,
}: {
  terms: OntologyTerm[];
  emptyMessage: string;
  showDetails: boolean;
  onPick: (term: OntologyTerm) => void;
  depth?: number;
}) {
  if (terms.length === 0 && depth === 0) {
    return <p className="px-4 py-1 text-xs text-slate-500">{emptyMessage}</p>;
  }
  return (
    <ul className={depth === 0 ? 'px-2 pb-2' : ''}>
      {terms.map((term) => (
        <li key={term.iri} style={{ paddingLeft: depth * 12 }}>
          <button
            type="button"
            draggable
            onDragStart={(event) => {
              event.dataTransfer.setData(CLASS_DRAG_TYPE, term.iri);
              event.dataTransfer.effectAllowed = 'copy';
            }}
            onClick={() => onPick(term)}
            className="w-full rounded px-2 py-1 text-left hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            {term.label}
            <span className="ml-1 text-xs text-slate-400">{term.instanceCount}</span>
            {showDetails && (
              <span className="block text-[10px] text-slate-400">{shortIri(term.iri)}</span>
            )}
          </button>
          {term.children.length > 0 && (
            <TermTree
              terms={term.children}
              emptyMessage={emptyMessage}
              showDetails={showDetails}
              onPick={onPick}
              depth={depth + 1}
            />
          )}
        </li>
      ))}
    </ul>
  );
}
