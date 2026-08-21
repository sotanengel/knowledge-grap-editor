/**
 * The two Cytoscape extensions ship without types.
 *
 * This file is a global script (no top-level import or export) so that the
 * declarations below create the missing modules rather than augmenting them.
 */
declare module 'cytoscape-edgehandles' {
  const extension: (cytoscape: unknown) => void;
  export default extension;
}

declare module 'cytoscape-fcose' {
  const extension: (cytoscape: unknown) => void;
  export default extension;
}
