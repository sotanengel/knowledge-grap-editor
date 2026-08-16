import { useEffect, useState } from "react";
import { api } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import PropertyForm from "../../components/ui/PropertyForm";
import { useToast } from "../../hooks/useToast";
import { slugFromLabel, uniqueId } from "../../utils/idSlug";

interface Props {
  onCreated: () => void;
  onCancel: () => void;
}

export default function NodeCreateForm({ onCreated, onCancel }: Props) {
  const { showToast } = useToast();
  const [label, setLabel] = useState("");
  const [nodeId, setNodeId] = useState("");
  const [type, setType] = useState("");
  const [description, setDescription] = useState("");
  const [properties, setProperties] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!label.trim()) return;
    const base = slugFromLabel(label);
    api
      .listNodes()
      .then((nodes) => {
        const ids = new Set(nodes.map((n) => n.id));
        setNodeId(uniqueId(base, ids));
      })
      .catch(() => setNodeId(base));
  }, [label]);

  const handleCreate = async () => {
    if (!label.trim() || !type) {
      setError("名前と型は必須です");
      return;
    }
    setError("");
    setSaving(true);
    try {
      const props = { ...properties };
      if (description) props.description = description;
      if (!props.name) props.name = label;
      await api.createNode({ id: nodeId, label, type, properties: props });
      showToast("success", "Nodeを作成しました");
      onCreated();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Nodeの作成に失敗しました";
      setError(msg);
      showToast("error", msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div data-testid="node-create-form">
      <h3>Nodeを追加</h3>
      <label>
        名前
        <input value={label} onChange={(e) => setLabel(e.target.value)} />
      </label>
      <label>
        型
        <Combobox value={type} onChange={setType} mode="class" placeholder="型を検索..." />
      </label>
      <label>
        説明
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label>
        ID
        <input value={nodeId} onChange={(e) => setNodeId(e.target.value)} />
      </label>
      <PropertyForm classId={type} values={properties} onChange={setProperties} />
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
