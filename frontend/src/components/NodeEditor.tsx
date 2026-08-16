import { useState } from "react";
import { api, Node } from "../api/client";
import TypeSuggest from "./TypeSuggest";

interface Props {
  node?: Node | null;
  onSave: () => void;
  onDelete?: () => void;
}

export default function NodeEditor({ node, onSave, onDelete }: Props) {
  const [id, setId] = useState(node?.id || "");
  const [label, setLabel] = useState(node?.label || "");
  const [type, setType] = useState(node?.type || "");
  const [properties, setProperties] = useState(
    node ? Object.entries(node.properties).map(([k, v]) => `${k}=${v}`).join("\n") : "",
  );
  const [error, setError] = useState("");

  const parseProperties = (): Record<string, string> => {
    const props: Record<string, string> = {};
    properties.split("\n").forEach((line) => {
      const [k, ...rest] = line.split("=");
      if (k && rest.length) props[k.trim()] = rest.join("=").trim();
    });
    return props;
  };

  const handleSave = async () => {
    setError("");
    try {
      const props = parseProperties();
      if (node) {
        await api.updateNode(node.id, { label, type, properties: props });
      } else {
        await api.createNode({ id, label, type, properties: props });
      }
      onSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存に失敗しました");
    }
  };

  const handleDelete = async () => {
    if (!node || !confirm("このノードを削除しますか？接続エッジも削除されます。")) return;
    try {
      await api.deleteNode(node.id);
      onDelete?.();
      onSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : "削除に失敗しました");
    }
  };

  return (
    <div className="editor-panel">
      <h3>{node ? "ノード編集" : "ノード作成"}</h3>
      {!node && (
        <label>
          ID
          <input value={id} onChange={(e) => setId(e.target.value)} />
        </label>
      )}
      <label>
        ラベル
        <input value={label} onChange={(e) => setLabel(e.target.value)} />
      </label>
      <label>
        型
        <TypeSuggest value={type} onChange={setType} />
      </label>
      <label>
        プロパティ (key=value)
        <textarea
          value={properties}
          onChange={(e) => setProperties(e.target.value)}
          rows={4}
        />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="btn-row">
        <button type="button" onClick={handleSave}>保存</button>
        {node && (
          <button type="button" className="danger" onClick={handleDelete}>削除</button>
        )}
      </div>
    </div>
  );
}
