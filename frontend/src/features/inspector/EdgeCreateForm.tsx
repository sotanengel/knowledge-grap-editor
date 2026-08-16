import { useState } from "react";
import type { Node } from "../../api/client";
import { api } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import NodePicker from "../../components/ui/NodePicker";
import { useToast } from "../../hooks/useToast";
import { slugFromLabel, uniqueId } from "../../utils/idSlug";

interface Props {
  nodes: Node[];
  defaultSubject?: string;
  onCreated: () => void;
  onCancel: () => void;
}

export default function EdgeCreateForm({
  nodes,
  defaultSubject = "",
  onCreated,
  onCancel,
}: Props) {
  const { showToast } = useToast();
  const [subject, setSubject] = useState(defaultSubject);
  const [predicate, setPredicate] = useState("");
  const [object, setObject] = useState("");
  const [edgeId, setEdgeId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    if (!subject || !predicate || !object) {
      setError("From、Relationship、To は必須です");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const id =
        edgeId ||
        uniqueId(
          slugFromLabel(`${predicate}-${subject}-${object}`),
          new Set((await api.listEdges()).map((e) => e.id)),
        );
      await api.createEdge({ id, subject, predicate, object, properties: {} });
      showToast("success", "Relationshipを作成しました");
      onCreated();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Relationshipの作成に失敗しました";
      setError(msg);
      showToast("error", msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="edge-create-form">
      <h3>Relationshipを追加</h3>
      <label>
        From
        <NodePicker nodes={nodes} value={subject} onChange={setSubject} />
      </label>
      <label>
        Relationship
        <Combobox
          value={predicate}
          onChange={setPredicate}
          mode="relationship"
          placeholder="関係を検索..."
        />
      </label>
      <label>
        To
        <NodePicker nodes={nodes} value={object} onChange={setObject} />
      </label>
      <label>
        ID（任意）
        <input value={edgeId} onChange={(e) => setEdgeId(e.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="btn-row">
        <button type="button" className="btn-secondary" onClick={onCancel}>
          キャンセル
        </button>
        <button type="button" onClick={handleCreate} disabled={saving}>
          {saving ? "作成中..." : "作成"}
        </button>
      </div>
    </div>
  );
}
