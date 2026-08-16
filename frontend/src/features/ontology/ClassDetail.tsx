import type { OwlClassV2, OwlPropertyV2 } from "../../api/client";

interface Props {
  cls: OwlClassV2;
  properties: OwlPropertyV2[];
  relationships: OwlPropertyV2[];
}

function formatSubclass(item: string | Record<string, unknown>): string {
  if (typeof item === "string") return item;
  if (item.kind === "named" && typeof item.iri === "string") {
    return item.iri.split(":").pop() ?? item.iri;
  }
  return JSON.stringify(item);
}

export default function ClassDetail({ cls, properties, relationships }: Props) {
  const jaLabel = cls.labels?.[0] ?? cls.label;

  return (
    <div className="ontology-class-detail" data-testid="class-detail">
      <h2>{cls.id}</h2>
      <div className="inspector-field">
        <label>IRI</label>
        <div className="value">{cls.iri}</div>
      </div>
      {jaLabel && (
        <div className="inspector-field">
          <label>表示名</label>
          <div className="value">{jaLabel}</div>
        </div>
      )}
      {cls.description && (
        <div className="inspector-field">
          <label>説明</label>
          <div className="value">{cls.description}</div>
        </div>
      )}
      {cls.subclass_of.length > 0 && (
        <div className="detail-section">
          <h4>subClassOf</h4>
          <ul className="ontology-list">
            {cls.subclass_of.map((s, i) => (
              <li key={i}>{formatSubclass(s)}</li>
            ))}
          </ul>
        </div>
      )}
      {cls.disjoint_with.length > 0 && (
        <div className="detail-section">
          <h4>disjointWith</h4>
          <ul className="ontology-list">
            {cls.disjoint_with.map((d, i) => (
              <li key={i}>{formatSubclass(d)}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="detail-section">
        <h4>Datatype Properties</h4>
        <ul className="ontology-list">
          {properties.map((p) => (
            <li key={p.id}>
              <strong>{p.id}</strong>
              <span>
                {p.description || p.label}
                {p.editor_required ? " (editor required)" : ""}
                {p.characteristics.length > 0 ? ` [${p.characteristics.join(", ")}]` : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="detail-section">
        <h4>Object Properties</h4>
        <ul className="ontology-list">
          {relationships.map((r) => (
            <li key={r.id}>
              <strong>{r.id}</strong>
              <span>
                {r.description || r.label}
                {r.inverse_of ? ` (inverse: ${r.inverse_of})` : ""}
                {r.characteristics.length > 0 ? ` [${r.characteristics.join(", ")}]` : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
