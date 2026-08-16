import type { LayoutName } from "../graph/nodeStyles";

interface Props {
  layout: LayoutName;
  onLayoutChange: (layout: LayoutName) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
}

export default function GraphControls({
  layout,
  onLayoutChange,
  onZoomIn,
  onZoomOut,
  onFit,
}: Props) {
  return (
    <div className="graph-controls" data-testid="graph-controls">
      <button type="button" aria-label="Zoom in" onClick={onZoomIn}>
        +
      </button>
      <button type="button" aria-label="Zoom out" onClick={onZoomOut}>
        −
      </button>
      <button type="button" aria-label="Fit view" onClick={onFit}>
        Fit
      </button>
      <select
        aria-label="Layout"
        value={layout}
        onChange={(e) => onLayoutChange(e.target.value as LayoutName)}
      >
        <option value="force">Force</option>
        <option value="hierarchical">Hierarchical</option>
        <option value="radial">Radial</option>
      </select>
    </div>
  );
}
