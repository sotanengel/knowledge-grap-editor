interface Props {
  classes: string[];
  relationships: string[];
  selectedClasses: Set<string>;
  selectedRelationships: Set<string>;
  onToggleClass: (id: string) => void;
  onToggleRelationship: (id: string) => void;
}

export default function FilterPanel({
  classes,
  relationships,
  selectedClasses,
  selectedRelationships,
  onToggleClass,
  onToggleRelationship,
}: Props) {
  return (
    <section data-testid="filter-panel">
      <h3>Filter</h3>
      <div className="filter-checkboxes">
        <p className="hint">Class</p>
        {classes.map((c) => (
          <label key={c}>
            <input
              type="checkbox"
              checked={selectedClasses.has(c)}
              onChange={() => onToggleClass(c)}
            />
            {c}
          </label>
        ))}
      </div>
      <div className="filter-checkboxes">
        <p className="hint">Relationship</p>
        {relationships.map((r) => (
          <label key={r}>
            <input
              type="checkbox"
              checked={selectedRelationships.has(r)}
              onChange={() => onToggleRelationship(r)}
            />
            {r}
          </label>
        ))}
      </div>
    </section>
  );
}
