import { useEffect, useState } from "react";
import { api, OwlClassV2, OwlPropertyV2 } from "../../api/client";
import ClassDetail from "./ClassDetail";

export default function OntologyExplorer() {
  const [classes, setClasses] = useState<OwlClassV2[]>([]);
  const [properties, setProperties] = useState<OwlPropertyV2[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [consistency, setConsistency] = useState<boolean | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getSchemaV2(), api.getConsistency()])
      .then(([schema, report]) => {
        setClasses(schema.classes);
        setProperties(schema.properties);
        setConsistency(report.consistent);
        if (schema.classes.length > 0) setSelectedId(schema.classes[0].id);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "取得に失敗しました"));
  }, []);

  const selected = classes.find((c) => c.id === selectedId);
  const classProperties = properties.filter(
    (p) =>
      p.property_type === "DatatypeProperty" &&
      (!p.domain.length || p.domain.includes(selectedId)),
  );
  const classRelationships = properties.filter(
    (p) =>
      p.property_type === "ObjectProperty" &&
      (p.domain.includes(selectedId) || p.range.includes(selectedId)),
  );

  if (error) {
    return (
      <div className="error-panel">
        <p className="error">{error}</p>
      </div>
    );
  }

  return (
    <div className="ontology-explorer" data-testid="ontology-explorer">
      <aside className="ontology-class-list">
        <h3>Classes (OWL 2 DL)</h3>
        {consistency !== null && (
          <p className="ontology-consistency" data-testid="consistency-status">
            {consistency ? "整合性: OK" : "整合性: 矛盾あり"}
          </p>
        )}
        <ul className="ontology-list">
          {classes.map((c) => (
            <li
              key={c.id}
              className={c.id === selectedId ? "selected" : ""}
              onClick={() => setSelectedId(c.id)}
            >
              <strong>{c.id}</strong>
              <span>{c.label || c.description}</span>
            </li>
          ))}
        </ul>
      </aside>
      {selected && (
        <ClassDetail
          cls={selected}
          properties={classProperties}
          relationships={classRelationships}
        />
      )}
    </div>
  );
}
