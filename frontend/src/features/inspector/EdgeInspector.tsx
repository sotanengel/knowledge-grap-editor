import { useEffect, useMemo, useState } from "react";
import { api, Edge, Node, Relationship } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import PropertyForm from "../../components/ui/PropertyForm";
import { filterRelationshipsByNodes, validateEdge } from "../../utils/graphValidation";

interface Props {
  edge: Edge;
  nodes: Node[];
  onSave: () => void;
  onDelete: () => void;
  onSelectNode?: (node: Node) => void;
}

export default function EdgeInspector({ edge, nodes, onSave, onDelete, onSelectNode }: Props) {
  const [editing, setEditing] = useState(false);
  const [subject, setSubject] = useState(edge.subject);
  const [predicate, setPredicate] = useState(edge.predicate);
  const [object, setObject] = useState(edge.object);
  const [properties, setProperties] = useState(edge.properties);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [existingEdges, setExistingEdges] = useState<Edge[]>([]);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

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

  const nodeLabel = (id: string) => nodes.find((n) => n.id === id)?.label ?? id;
  const fromNode = nodes.find((n) => n.id === edge.subject);
  const toNode = nodes.find((n) => n.id === edge.object);

  const handleSave = async () => {
    const validation = validateEdge(
      { id: edge.id, subject, predicate, object },
      relationships,
      nodes,
      { existingEdges, editingEdgeId: edge.id },
    );
    if (!validation.valid) {
      setFieldErrors(validation.fieldErrors);
      setError(validation.formError ?? "入力内容を確認してください");
      return;
    }

    setError("");
    setFieldErrors({});
    setSaving(true);
    try {
      await api.updateEdge(edge.id, { subject, predicate, object, properties });
      setEditing(false);
      onSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteEdge(edge.id);
      setConfirmDelete(false);
      onDelete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "削除に失敗しました");
    }
  };

  return (
    <div data-testid="edge-inspector">
      <h3>Relationship</h3>
      {!editing ? (
        <>
          <div className="inspector-field">
            <label>Type</label>
            <div className="value">{edge.predicate}</div>
          </div>
          <div className="inspector-field">
            <label>From</label>
            <div className="value">
              {fromNode ? (
                <button
                  type="button"
                  className="link-btn"
                  onClick={() => onSelectNode?.(fromNode)}
                >
                  {fromNode.label}
                </button>
              ) : (
                nodeLabel(edge.subject)
              )}
            </div>
          </div>
          <div className="inspector-field">
            <label>To</label>
            <div className="value">
              {toNode ? (
                <button type="button" className="link-btn" onClick={() => onSelectNode?.(toNode)}>
                  {toNode.label}
                </button>
              ) : (
                nodeLabel(edge.object)
              )}
            </div>
          </div>
          <h4>Properties</h4>
          <PropertyForm
            classId=""
            values={edge.properties}
            onChange={() => {}}
            readOnly
          />
          <div className="btn-row">
            <button type="button" onClick={() => setEditing(true)}>
              編集
            </button>
            <button type="button" className="btn-danger" onClick={() => setConfirmDelete(true)}>
              削除
            </button>
          </div>
        </>
      ) : (
        <>
          <label>
            From
            <select value={subject} onChange={(e) => setSubject(e.target.value)}>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.label}
                </option>
              ))}
            </select>
            {fieldErrors.subject && <span className="field-error">{fieldErrors.subject}</span>}
          </label>
          <label>
            Relationship
            <Combobox
              value={predicate}
              onChange={setPredicate}
              mode="relationship"
              filterIds={predicateFilterIds}
            />
            {fieldErrors.predicate && <span className="field-error">{fieldErrors.predicate}</span>}
          </label>
          <label>
            To
            <select value={object} onChange={(e) => setObject(e.target.value)}>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.label}
                </option>
              ))}
            </select>
            {fieldErrors.object && <span className="field-error">{fieldErrors.object}</span>}
          </label>
          <PropertyForm classId="" values={properties} onChange={setProperties} />
          {error && <p className="error">{error}</p>}
          <div className="btn-row">
            <button type="button" onClick={handleSave} disabled={saving}>
              {saving ? "保存中..." : "保存"}
            </button>
            <button type="button" className="btn-secondary" onClick={() => setEditing(false)}>
              キャンセル
            </button>
          </div>
        </>
      )}
      <ConfirmDialog
        open={confirmDelete}
        title="Relationshipの削除"
        message={`「${edge.predicate}」を削除しますか？`}
        confirmLabel="削除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
