interface Props {
  showNodeType: boolean;
  showRelationship: boolean;
  showLabel: boolean;
  showDescription: boolean;
  onChange: (key: string, value: boolean) => void;
}

export default function DisplaySettings({
  showNodeType,
  showRelationship,
  showLabel,
  showDescription,
  onChange,
}: Props) {
  return (
    <section data-testid="display-settings">
      <h3>表示設定</h3>
      <div className="filter-checkboxes">
        <label>
          <input
            type="checkbox"
            checked={showNodeType}
            onChange={(e) => onChange("nodeType", e.target.checked)}
          />
          Node Type
        </label>
        <label>
          <input
            type="checkbox"
            checked={showRelationship}
            onChange={(e) => onChange("relationship", e.target.checked)}
          />
          Relationship
        </label>
        <label>
          <input
            type="checkbox"
            checked={showLabel}
            onChange={(e) => onChange("label", e.target.checked)}
          />
          Label
        </label>
        <label>
          <input
            type="checkbox"
            checked={showDescription}
            onChange={(e) => onChange("description", e.target.checked)}
          />
          Description
        </label>
      </div>
    </section>
  );
}
