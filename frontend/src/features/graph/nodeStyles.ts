type CytoscapeStyle = {
  selector: string;
  style: Record<string, string | number>;
};

export const TYPE_ICONS: Record<string, string> = {
  Person: "👤",
  Organization: "🏢",
  Product: "📦",
  Place: "📍",
  Event: "📅",
  Document: "📄",
  Software: "💻",
  Project: "📁",
  Agent: "🤖",
};

export const TYPE_LABELS: Record<string, string> = {
  Person: "Person",
  Organization: "Organization",
  Product: "Product",
  Place: "Place",
  Event: "Event",
  Document: "Document",
  Software: "Software",
  Project: "Project",
  Agent: "Agent",
};

const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Person: { bg: "#eff6ff", border: "#3b82f6", text: "#1e40af" },
  Organization: { bg: "#f0fdf4", border: "#22c55e", text: "#166534" },
  Product: { bg: "#fefce8", border: "#eab308", text: "#854d0e" },
  Place: { bg: "#fdf4ff", border: "#a855f7", text: "#6b21a8" },
  Event: { bg: "#fff7ed", border: "#f97316", text: "#9a3412" },
  Document: { bg: "#f8fafc", border: "#64748b", text: "#334155" },
  Software: { bg: "#ecfeff", border: "#06b6d4", text: "#155e75" },
  Project: { bg: "#fef2f2", border: "#ef4444", text: "#991b1b" },
  Agent: { bg: "#f5f3ff", border: "#8b5cf6", text: "#5b21b6" },
};

const DEFAULT_COLOR = { bg: "#f1f5f9", border: "#64748b", text: "#334155" };

export function getTypeIcon(type: string): string {
  return TYPE_ICONS[type] ?? "◆";
}

export function getTypeDisplayLabel(type: string): string {
  const icon = getTypeIcon(type);
  const label = TYPE_LABELS[type] ?? type;
  return `${icon} ${label}`;
}

export function buildNodeLabel(type: string, label: string, primaryAttr?: string): string {
  const typeLine = getTypeDisplayLabel(type);
  if (primaryAttr) {
    return `${typeLine}\n${label}\n${primaryAttr}`;
  }
  return `${typeLine}\n${label}`;
}

export function getNodeStyleForType(type: string): Record<string, string | number> {
  const colors = TYPE_COLORS[type] ?? DEFAULT_COLOR;
  return {
    "background-color": colors.bg,
    "border-color": colors.border,
    color: colors.text,
  };
}

export function buildCytoscapeStyles(): CytoscapeStyle[] {
  const baseNodeStyle: CytoscapeStyle = {
    selector: "node",
    style: {
      shape: "round-rectangle",
      label: "data(displayLabel)",
      "text-valign": "center",
      "text-halign": "center",
      "font-size": "9px",
      "text-wrap": "wrap",
      "text-max-width": "100px",
      width: 120,
      height: 70,
      "background-color": DEFAULT_COLOR.bg,
      "border-width": 2,
      "border-color": DEFAULT_COLOR.border,
      color: DEFAULT_COLOR.text,
      padding: "8px",
    },
  };

  const typeStyles: CytoscapeStyle[] = Object.keys(TYPE_COLORS).map((type) => ({
    selector: `node[type = "${type}"]`,
    style: getNodeStyleForType(type),
  }));

  return [
    baseNodeStyle,
    ...typeStyles,
    {
      selector: "node:selected",
      style: {
        "border-width": 3,
        "border-color": "#2563eb",
        "overlay-color": "#2563eb",
        "overlay-opacity": 0.1,
        "overlay-padding": 4,
      },
    },
    {
      selector: "node.edge-endpoint",
      style: {
        "border-width": 3,
        "border-color": "#f59e0b",
        "border-style": "dashed",
      },
    },
    {
      selector: "edge",
      style: {
        label: "data(label)",
        width: 2,
        "line-color": "#94a3b8",
        "target-arrow-color": "#94a3b8",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        "font-size": "8px",
        color: "#64748b",
        "text-background-color": "#ffffff",
        "text-background-opacity": 0.85,
        "text-background-padding": "2px",
      },
    },
    {
      selector: "edge:selected",
      style: {
        width: 3,
        "line-color": "#2563eb",
        "target-arrow-color": "#2563eb",
        color: "#2563eb",
      },
    },
  ];
}

export const LAYOUT_OPTIONS = {
  force: { name: "cose", animate: true },
  hierarchical: { name: "breadthfirst", animate: true, directed: true },
  radial: { name: "concentric", animate: true, concentric: () => 1 },
} as const;

export type LayoutName = keyof typeof LAYOUT_OPTIONS;
