/**
 * The graph canvas (FR-01, FR-02).
 *
 * Double-clicking empty space adds a node; dragging from a node's rim to another
 * node opens the property picker, filtered by domain and range (§7.2). Derived
 * edges are drawn dashed and refuse to be edited.
 */
import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type {
  Core,
  EdgeHandlesInstance,
  ElementDefinition,
  LayoutOptions,
  EdgeSingular,
  EventObject,
  NodeSingular,
} from 'cytoscape';
import edgehandles from 'cytoscape-edgehandles';
import fcose from 'cytoscape-fcose';

import { CLASS_DRAG_TYPE } from '../../lib/dragTypes';
import { buildElements, needsNeighbourhoodMode } from '../../lib/elements';
import { useGraph } from '../../state/graph';
import { useSettings } from '../../state/settings';
import { FIT_PADDING, GRAPH_STYLE, LAYOUT } from './style';
import { CreateNodeDialog } from './CreateNodeDialog';
import { CreateEdgeDialog } from './CreateEdgeDialog';

cytoscape.use(edgehandles);
cytoscape.use(fcose);

interface PendingEdge {
  source: string;
  target: string;
}

export function GraphCanvas() {
  const container = useRef<HTMLDivElement>(null);
  const core = useRef<Core | null>(null);
  const handles = useRef<EdgeHandlesInstance | null>(null);
  /** Once the user has moved the view, stop refitting it for them. */
  const userMoved = useRef(false);

  const { entities, inferredEdges, validation, selected, select, refresh } = useGraph();
  const { terms } = useSettings();

  const [creating, setCreating] = useState<{ type?: string } | null>(null);
  const [pendingEdge, setPendingEdge] = useState<PendingEdge | null>(null);
  const [connectMode, setConnectMode] = useState(false);
  const [dropTarget, setDropTarget] = useState(false);

  // ---------------------------------------------------------------- set-up

  useEffect(() => {
    if (!container.current) return undefined;

    const instance = cytoscape({
      container: container.current,
      style: GRAPH_STYLE,
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 3,
    });
    core.current = instance;

    const eh = instance.edgehandles({
      snap: true,
      canConnect: (source, target) => !source.same(target),
      edgeParams: () => ({ data: { pending: true } }),
    });
    eh.disableDrawMode();
    handles.current = eh;

    instance.on('tap', 'node', (event: EventObject) => {
      select((event.target as NodeSingular).id());
    });

    instance.on('tap', (event: EventObject) => {
      if (event.target === instance) select(null);
    });

    instance.on('dbltap', (event: EventObject) => {
      if (event.target === instance) setCreating({});
    });

    // edgehandles draws a provisional edge; it is removed straight away and the
    // real one is only written once the user has picked a property.
    instance.on(
      'ehcomplete',
      (_event: EventObject, source: NodeSingular, target: NodeSingular, added: EdgeSingular) => {
        added.remove();
        setPendingEdge({ source: source.id(), target: target.id() });
      },
    );

    // Cytoscape caches the container size, and at mount the flex layout has not
    // settled yet, so without this the graph ends up squeezed into a corner.
    // Refitting on resize keeps it centred while the window changes -- but only
    // until the user pans or zooms, after which their view is left alone.
    instance.on('dragpan zoom', (event: EventObject) => {
      if (event.type === 'zoom' && !instance.userZoomingEnabled()) return;
      userMoved.current = true;
    });

    const observer = new ResizeObserver(() => {
      instance.resize();
      if (!userMoved.current && instance.elements().length > 0) {
        instance.fit(undefined, FIT_PADDING);
      }
    });
    observer.observe(container.current);

    return () => {
      observer.disconnect();
      instance.destroy();
      core.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------------------------------------------------------- data

  useEffect(() => {
    const instance = core.current;
    if (!instance) return;

    const positions: Record<string, { x: number; y: number }> = {};
    instance.nodes().forEach((node) => {
      positions[node.id()] = node.position();
    });

    const elements = buildElements(entities, {
      inferredEdges,
      violated: new Set(validation?.violated ?? []),
      positions,
    });

    instance.batch(() => {
      instance.elements().remove();
      instance.add(elements as ElementDefinition[]);
    });

    const unplaced = instance.nodes().filter((node) => !positions[node.id()]);
    if (unplaced.length === 0) return;

    instance.resize();
    const layout = instance.layout(LAYOUT as unknown as LayoutOptions);
    layout.one('layoutstop', () => {
      instance.resize();
      if (!userMoved.current) instance.fit(undefined, FIT_PADDING);
    });
    layout.run();
  }, [entities, inferredEdges, validation]);

  useEffect(() => {
    const instance = core.current;
    if (!instance) return;
    instance.nodes().unselect();
    if (selected) instance.getElementById(selected).select();
  }, [selected]);

  useEffect(() => {
    if (!handles.current) return;
    if (connectMode) handles.current.enableDrawMode();
    else handles.current.disableDrawMode();
  }, [connectMode]);

  // ---------------------------------------------------------------- render

  const tooMany = needsNeighbourhoodMode(entities.length);

  return (
    <div className="relative flex h-full w-full flex-col" data-testid="graph-canvas">
      <div className="flex shrink-0 items-center gap-2 border-b border-slate-200 bg-white px-3 py-1.5 dark:border-slate-800 dark:bg-slate-900">
        <button
          type="button"
          onClick={() => setConnectMode((on) => !on)}
          aria-pressed={connectMode}
          className={`rounded-md border px-3 py-1 text-xs ${
            connectMode
              ? 'border-blue-600 bg-blue-600 text-white'
              : 'border-slate-300 text-slate-700 dark:border-slate-600 dark:text-slate-200'
          }`}
        >
          {connectMode ? `${terms.relation}を引く（ドラッグ）` : `${terms.relation}を引く`}
        </button>
        <button
          type="button"
          onClick={() => setCreating({})}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-700 dark:border-slate-600 dark:text-slate-200"
        >
          ＋ {terms.instance}を追加
        </button>
        <button
          type="button"
          onClick={() => {
            userMoved.current = false;
            core.current?.fit(undefined, FIT_PADDING);
          }}
          className="ml-auto rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-700 dark:border-slate-600 dark:text-slate-200"
        >
          全体を表示
        </button>
      </div>

      <div
        ref={container}
        className={`min-h-0 flex-1 bg-slate-50 dark:bg-slate-900 ${
          dropTarget ? 'ring-2 ring-inset ring-blue-500' : ''
        }`}
        onDragOver={(event) => {
          if (!event.dataTransfer.types.includes(CLASS_DRAG_TYPE)) return;
          event.preventDefault();
          event.dataTransfer.dropEffect = 'copy';
          setDropTarget(true);
        }}
        onDragLeave={() => setDropTarget(false)}
        onDrop={(event) => {
          const type = event.dataTransfer.getData(CLASS_DRAG_TYPE);
          setDropTarget(false);
          if (!type) return;
          event.preventDefault();
          setCreating({ type });
        }}
      />

      {entities.length === 0 && (
        <p className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-slate-500">
          空白をダブルクリックすると{terms.instance}を追加できます。 左の{terms.class}
          をここへドラッグしてもかまいません。
        </p>
      )}

      {tooMany && (
        <p
          role="status"
          className="absolute bottom-3 left-3 rounded-md bg-amber-100 px-3 py-1.5 text-xs text-amber-900 dark:bg-amber-900/40 dark:text-amber-100"
        >
          {entities.length} 件あります。検索で絞り込むと快適に操作できます。
        </p>
      )}

      {creating && (
        <CreateNodeDialog
          initialType={creating.type}
          onClose={() => setCreating(null)}
          onCreated={async (iri) => {
            setCreating(null);
            await refresh();
            select(iri);
          }}
        />
      )}

      {pendingEdge && (
        <CreateEdgeDialog
          source={pendingEdge.source}
          target={pendingEdge.target}
          onClose={() => setPendingEdge(null)}
          onCreated={async () => {
            setPendingEdge(null);
            await refresh();
          }}
        />
      )}
    </div>
  );
}
