import { useEffect, useState } from "react";
import { api, OntologyClass, PropertyDef, Relationship } from "../../api/client";
import ClassDetail from "./ClassDetail";

export default function OntologyExplorer() {
  const [classes, setClasses] = useState<OntologyClass[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [properties, setProperties] = useState<PropertyDef[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.listClasses(), api.listRelationships()])
      .then(([c, r]) => {
        setClasses(c);
        setRelationships(r);
        if (c.length > 0) setSelectedId(c[0].id);
        setError("");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "取得に失敗しました"));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    api
      .getClassProperties(selectedId)
      .then(setProperties)
      .catch(() => setProperties([]));
  }, [selectedId]);

  const selected = classes.find((c) => c.id === selectedId);
  const classRelationships = relationships.filter(
    (r) => r.domain.includes(selectedId) || r.range.includes(selectedId),
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
        <h3>Classes</h3>
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
          properties={properties}
          relationships={classRelationships}
        />
      )}
    </div>
  );
}
