import type { Node } from "../../api/client";
import DisplaySettings from "./DisplaySettings";
import FilterPanel from "./FilterPanel";
import SearchPanel from "./SearchPanel";

interface Props {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSearch: (q: string) => void;
  searchResults: Node[];
  onSelectResult: (node: Node) => void;
  depth: number;
  onDepthChange: (d: number) => void;
  classes: string[];
  relationships: string[];
  selectedClasses: Set<string>;
  selectedRelationships: Set<string>;
  onToggleClass: (id: string) => void;
  onToggleRelationship: (id: string) => void;
  displaySettings: {
    showNodeType: boolean;
    showRelationship: boolean;
    showLabel: boolean;
    showDescription: boolean;
  };
  onDisplayChange: (key: string, value: boolean) => void;
  onAddNode?: () => void;
  onAddRelationship?: () => void;
  leftCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function LeftNavigator({
  searchQuery,
  onSearchChange,
  onSearch,
  searchResults,
  onSelectResult,
  depth,
  onDepthChange,
  classes,
  relationships,
  selectedClasses,
  selectedRelationships,
  onToggleClass,
  onToggleRelationship,
  displaySettings,
  onDisplayChange,
  onAddNode,
  onAddRelationship,
  leftCollapsed,
  onToggleCollapse,
}: Props) {
  return (
    <div className="navigator-panel" data-testid="left-navigator">
      {onToggleCollapse && (
        <button type="button" className="btn-secondary collapse-toggle" onClick={onToggleCollapse}>
          {leftCollapsed ? "▶" : "◀"}
        </button>
      )}
      <SearchPanel
        query={searchQuery}
        onQueryChange={onSearchChange}
        onSearch={onSearch}
        results={searchResults}
        onSelectResult={onSelectResult}
      />
      <section>
        <h3>探索深度</h3>
        <select
          value={depth}
          onChange={(e) => onDepthChange(Number(e.target.value))}
          aria-label="探索深度"
        >
          <option value={1}>1-hop</option>
          <option value={2}>2-hop</option>
          <option value={3}>3-hop</option>
        </select>
      </section>
      <FilterPanel
        classes={classes}
        relationships={relationships}
        selectedClasses={selectedClasses}
        selectedRelationships={selectedRelationships}
        onToggleClass={onToggleClass}
        onToggleRelationship={onToggleRelationship}
      />
      <DisplaySettings {...displaySettings} onChange={onDisplayChange} />
      <section>
        <div className="btn-row">
          <button type="button" onClick={onAddNode}>
            + Node
          </button>
          <button type="button" className="btn-secondary" onClick={onAddRelationship}>
            + Relationship
          </button>
        </div>
      </section>
    </div>
  );
}
