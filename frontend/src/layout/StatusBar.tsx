interface Props {
  nodeCount?: number;
  edgeCount?: number;
  selection?: string;
  zoom?: number;
}

export default function StatusBar({
  nodeCount = 0,
  edgeCount = 0,
  selection = "",
  zoom,
}: Props) {
  return (
    <footer className="status-bar" data-testid="status-bar">
      <span>
        {nodeCount} Nodes / {edgeCount} Relationships
        {selection && ` · ${selection}`}
      </span>
      <span>{zoom !== undefined ? `Zoom ${Math.round(zoom * 100)}%` : ""}</span>
    </footer>
  );
}
