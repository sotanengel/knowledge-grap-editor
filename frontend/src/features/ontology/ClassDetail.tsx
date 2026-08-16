import type { OntologyClass, PropertyDef, Relationship } from "../../api/client";

interface Props {
  cls: OntologyClass;
  properties: PropertyDef[];
  relationships: Relationship[];
}

export default function ClassDetail({ cls, properties, relationships }: Props) {
  const jaLabel = cls.labels?.[0] ?? cls.label;

  return (
    <div className="ontology-class-detail" data-testid="class-detail">
      <h2>{cls.id}</h2>
      {jaLabel && (
        <div className="inspector-field">
          <label>日本語名</label>
          <div className="value">{jaLabel}</div>
        </div>
      )}
      {cls.description && (
        <div className="inspector-field">
          <label>説明</label>
          <div className="value">{cls.description}</div>
        </div>
      )}
      <div className="detail-section">
        <h4>Properties</h4>
        <ul className="ontology-list">
          {properties.map((p) => (
            <li key={p.id}>
              <strong>{p.id}</strong>
              <span>{p.description || p.label}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="detail-section">
        <h4>Relationships</h4>
        <ul className="ontology-list">
          {relationships.map((r) => (
            <li key={r.id}>
              <strong>{r.id}</strong>
              <span>{r.description || r.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
