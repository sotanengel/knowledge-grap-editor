import { useEffect, useState } from "react";
import { api, OntologyClass, Relationship } from "../api/client";

interface Props {
  onChange?: () => void;
}

export default function OntologyPanel({ onChange }: Props) {
  const [classes, setClasses] = useState<OntologyClass[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [tab, setTab] = useState<"classes" | "relationships">("classes");
  const [newClassId, setNewClassId] = useState("");
  const [newClassLabel, setNewClassLabel] = useState("");
  const [newRelId, setNewRelId] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    const [c, r] = await Promise.all([api.listClasses(), api.listRelationships()]);
    setClasses(c);
    setRelationships(r);
  };

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const addClass = async () => {
    setError("");
    try {
      await api.createClass({
        id: newClassId,
        label: newClassLabel,
        description: "",
        aliases: [],
        parent_classes: [],
        examples: [],
      });
      setNewClassId("");
      setNewClassLabel("");
      await load();
      onChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Class 作成に失敗しました");
    }
  };

  const addRelationship = async () => {
    setError("");
    try {
      await api.createRelationship({
        id: newRelId,
        label: newRelId,
        description: "",
        domain: [],
        range: [],
        aliases: [],
      });
      setNewRelId("");
      await load();
      onChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Relationship 作成に失敗しました");
    }
  };

  return (
    <div className="ontology-panel">
      <h3>オントロジー</h3>
      <div className="tab-row">
        <button type="button" className={tab === "classes" ? "active" : ""} onClick={() => setTab("classes")}>
          Classes
        </button>
        <button type="button" className={tab === "relationships" ? "active" : ""} onClick={() => setTab("relationships")}>
          Relationships
        </button>
      </div>
      {tab === "classes" && (
        <>
          <ul className="ontology-list">
            {classes.map((c) => (
              <li key={c.id}>
                <strong>{c.id}</strong>
                <span>{c.description || c.label}</span>
              </li>
            ))}
          </ul>
          <div className="add-form">
            <input placeholder="Class ID" value={newClassId} onChange={(e) => setNewClassId(e.target.value)} />
            <input placeholder="Label" value={newClassLabel} onChange={(e) => setNewClassLabel(e.target.value)} />
            <button type="button" onClick={addClass}>追加</button>
          </div>
        </>
      )}
      {tab === "relationships" && (
        <>
          <ul className="ontology-list">
            {relationships.map((r) => (
              <li key={r.id}>
                <strong>{r.id}</strong>
                <span>{r.domain.join(", ")} → {r.range.join(", ")}</span>
              </li>
            ))}
          </ul>
          <div className="add-form">
            <input placeholder="Relationship ID" value={newRelId} onChange={(e) => setNewRelId(e.target.value)} />
            <button type="button" onClick={addRelationship}>追加</button>
          </div>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
