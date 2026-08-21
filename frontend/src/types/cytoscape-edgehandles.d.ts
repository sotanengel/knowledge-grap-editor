/**
 * `edgehandles` adds one method to the Cytoscape core.
 *
 * This file is a module (it imports), so the block below *augments* the real
 * cytoscape types instead of replacing them.
 */
import type { NodeSingular } from 'cytoscape';

declare module 'cytoscape' {
  interface EdgeHandlesInstance {
    enableDrawMode(): void;
    disableDrawMode(): void;
    destroy(): void;
  }

  interface Core {
    edgehandles(options: {
      snap?: boolean;
      canConnect?: (source: NodeSingular, target: NodeSingular) => boolean;
      edgeParams?: (source: NodeSingular, target: NodeSingular) => unknown;
    }): EdgeHandlesInstance;
  }
}
