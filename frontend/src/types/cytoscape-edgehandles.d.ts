import type { NodeSingular } from "cytoscape";
import "cytoscape";

declare module "cytoscape" {
  interface EdgeHandlesOptions {
    canConnect?: (sourceNode: NodeSingular, targetNode: NodeSingular) => boolean;
    edgeParams?: (sourceNode: NodeSingular, targetNode: NodeSingular) => Record<string, unknown>;
    hoverDelay?: number;
    snap?: boolean;
    snapThreshold?: number;
    snapFrequency?: number;
    noEdgeEventsInDraw?: boolean;
    disableBrowserGestures?: boolean;
  }

  interface EdgeHandlesInstance {
    enable: () => void;
    disable: () => void;
    destroy: () => void;
    start: (node: NodeSingular) => void;
    stop: () => void;
    enableDrawMode: () => void;
    disableDrawMode: () => void;
  }

  interface Core {
    edgehandles: (options?: EdgeHandlesOptions) => EdgeHandlesInstance;
  }
}

declare module "cytoscape-edgehandles" {
  import type { Ext } from "cytoscape";
  const edgehandles: Ext;
  export default edgehandles;
}

export {};
