import { useEffect, useMemo, useState } from "react";
import type { Edge, Node, Relationship } from "../../api/client";
import { api } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import NodePicker from "../../components/ui/NodePicker";
import { useToast } from "../../hooks/useToast";
import { filterRelationshipsByNodes, validateEdge } from "../../utils/graphValidation";
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
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [existingEdges, setExistingEdges] = useState<Edge[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    void api.listRelationships().then(setRelationships).catch(() => setRelationships([]));
    void api.listEdges().then(setExistingEdges).catch(() => setExistingEdges([]));
  }, []);

  const subjectNode = nodes.find((n) => n.id === subject);
  const objectNode = nodes.find((n) => n.id === object);

  const predicateFilterIds = useMemo(() => {
    if (!subjectNode || !objectNode) return undefined;
    const filtered = filterRelationshipsByNodes(subjectNode, objectNode, relationships);
    return new Set(filtered.map((r) => r.id));
  }, [subjectNode, objectNode, relationships]);

  useEffect(() => {
    if (predicate && predicateFilterIds && !predicateFilterIds.has(predicate)) {
      setPredicate("");
    }
  }, [predicate, predicateFilterIds]);

  const handleCreate = async () => {
    const validation = validateEdge(
      { subject, predicate, object },
      relationships,
      nodes,
      { existingEdges },
    );
    if (!validation.valid) {
      setFieldErrors(validation.fieldErrors);
      setError(validation.formError ?? "入力内容を確認してください");
      showToast("error", validation.formError ?? "入力内容を確認してください");
      return;
    }

    setError("");
    setFieldErrors({});
    setSaving(true);
    try {
      const id =
        edgeId ||
        uniqueId(
          slugFromLabel(`${predicate}-${subject}-${object}`),
          new Set(existingEdges.map((e) => e.id)),
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
        {fieldErrors.subject && <span className="field-error">{fieldErrors.subject}</span>}
      </label>
      <label>
        Relationship
        <Combobox
          value={predicate}
          onChange={setPredicate}
          mode="relationship"
          placeholder="関係を検索..."
          filterIds={predicateFilterIds}
        />
        {fieldErrors.predicate && <span className="field-error">{fieldErrors.predicate}</span>}
      </label>
      <label>
        To
        <NodePicker nodes={nodes} value={object} onChange={setObject} />
        {fieldErrors.object && <span className="field-error">{fieldErrors.object}</span>}
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
