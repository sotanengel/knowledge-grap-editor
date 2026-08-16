import { useState } from "react";
import { api, Edge, Node } from "../api/client";
import TypeSuggest from "./TypeSuggest";

interface Props {
  edge?: Edge | null;
  nodes: Node[];
  onSave: () => void;
  onDelete?: () => void;
}

export default function EdgeEditor({ edge, nodes, onSave, onDelete }: Props) {
  const [id, setId] = useState(edge?.id || "");
  const [subject, setSubject] = useState(edge?.subject || "");
  const [predicate, setPredicate] = useState(edge?.predicate || "");
  const [object, setObject] = useState(edge?.object || "");
  const [error, setError] = useState("");

  const handleSave = async () => {
    setError("");
    try {
      if (edge) {
        await api.updateEdge(edge.id, { subject, predicate, object });
      } else {
        await api.createEdge({ id, subject, predicate, object, properties: {} });
      }
      onSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存に失敗しました");
    }
  };

  const handleDelete = async () => {
    if (!edge || !confirm("このエッジを削除しますか？")) return;
    try {
      await api.deleteEdge(edge.id);
      onDelete?.();
      onSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : "削除に失敗しました");
    }
  };

  return (
    <div className="editor-panel">
      <h3>{edge ? "エッジ編集" : "エッジ作成"}</h3>
      {!edge && (
        <label>
          ID
          <input value={id} onChange={(e) => setId(e.target.value)} />
        </label>
      )}
      <label>
        Source
        <select value={subject} onChange={(e) => setSubject(e.target.value)}>
          <option value="">選択...</option>
          {nodes.map((n) => (
            <option key={n.id} value={n.id}>{n.label} ({n.id})</option>
          ))}
        </select>
      </label>
      <label>
        Relationship
        <TypeSuggest
          value={predicate}
          onChange={setPredicate}
          mode="relationship"
          placeholder="関係を入力..."
        />
      </label>
      <label>
        Target
        <select value={object} onChange={(e) => setObject(e.target.value)}>
          <option value="">選択...</option>
          {nodes.map((n) => (
            <option key={n.id} value={n.id}>{n.label} ({n.id})</option>
          ))}
        </select>
      </label>
      {error && <p className="error">{error}</p>}
      <div className="btn-row">
        <button type="button" onClick={handleSave}>保存</button>
        {edge && (
          <button type="button" className="danger" onClick={handleDelete}>削除</button>
        )}
      </div>
    </div>
  );
}
