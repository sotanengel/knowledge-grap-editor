import "cytoscape";

declare module "cytoscape" {
  interface EdgeHandlesOptions {
    preview?: boolean;
    handleNodes?: string;
    handlePosition?: (node: unknown) => string;
    loopAllowed?: () => boolean;
    complete?: (sourceNode: unknown, targetNode: unknown, addedEdge: { remove: () => void }) => void;
  }

  interface EdgeHandlesInstance {
    enable: () => void;
    disable: () => void;
    destroy: () => void;
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
