import { useEffect, useMemo, useState } from "react";
import { api, Edge, Node, OntologyClass, PropertyDef } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import ConfirmDialog from "../../components/ui/ConfirmDialog";
import PropertyForm from "../../components/ui/PropertyForm";
import { getTypeDisplayLabel } from "../graph/nodeStyles";
import { propertyErrorsForForm, validateNode } from "../../utils/graphValidation";
import { nodePropertiesWithLabel, resolveNodeLabel } from "../../utils/nodeLabel";

interface Props {
  node: Node;
  edges: Edge[];
  nodes: Node[];
  onSave: () => void;
  onDelete: () => void;
  onSelectEdge?: (edge: Edge) => void;
}

export default function NodeInspector({
  node,
  edges,
  nodes,
  onSave,
  onDelete,
  onSelectEdge,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [type, setType] = useState(node.type);
  const [properties, setProperties] = useState(() =>
    nodePropertiesWithLabel(node.label, node.properties),
  );
  const [propertyDefs, setPropertyDefs] = useState<PropertyDef[]>([]);
  const [classes, setClasses] = useState<OntologyClass[]>([]);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const relatedEdges = edges.filter((e) => e.subject === node.id || e.object === node.id);
  const displayProperties = nodePropertiesWithLabel(node.label, node.properties);
  const displayName = resolveNodeLabel(node);

  useEffect(() => {
    void api.listClasses().then(setClasses).catch(() => setClasses([]));
  }, []);

  useEffect(() => {
    if (!type) {
      setPropertyDefs([]);
      return;
    }
    void api
      .getClassProperties(type)
      .then(setPropertyDefs)
      .catch(() => setPropertyDefs([]));
  }, [type]);

  useEffect(() => {
    if (!editing) {
      setType(node.type);
      setProperties(nodePropertiesWithLabel(node.label, node.properties));
    }
  }, [node, editing]);

  const propertyFieldErrors = useMemo(() => propertyErrorsForForm(fieldErrors), [fieldErrors]);

  const handleSave = async () => {
    const label = resolveNodeLabel({ label: node.label, properties });

    let defs = propertyDefs;
    if (type && defs.length === 0) {
      try {
        defs = await api.getClassProperties(type);
        setPropertyDefs(defs);
      } catch {
        defs = [];
      }
    }

    let classList = classes;
    if (classList.length === 0) {
      try {
        classList = await api.listClasses();
        setClasses(classList);
      } catch {
        classList = [];
      }
    }

    const validation = validateNode(
      { id: node.id, label, type, properties },
      defs,
      classList,
      { editingNodeId: node.id },
    );
    if (!validation.valid) {
      setFieldErrors(validation.fieldErrors);
      setError("入力内容を確認してください");
      return;
    }

    setError("");
    setFieldErrors({});
    setSaving(true);
    try {
      await api.updateNode(node.id, { label, type, properties });
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
      await api.deleteNode(node.id);
      setConfirmDelete(false);
      onDelete();
    } catch (e) {
      setError(e instanceof Error ? e.message : "削除に失敗しました");
    }
  };

  const nodeLabel = (id: string) => {
    const n = nodes.find((item) => item.id === id);
    return n ? resolveNodeLabel(n) : id;
  };

  return (
    <div data-testid="node-inspector">
      <h3>Node</h3>
      {!editing ? (
        <>
          <div className="inspector-field">
            <label>Type</label>
            <div className="value">{getTypeDisplayLabel(node.type)}</div>
          </div>
          <div className="inspector-field">
            <label>ID</label>
            <div className="value">{node.id}</div>
          </div>
          <h4>Properties</h4>
          <PropertyForm
            classId={node.type}
            values={displayProperties}
            onChange={() => {}}
            readOnly
          />
          {relatedEdges.length > 0 && (
            <>
              <h4>Relationships</h4>
              <ul className="node-list">
                {relatedEdges.map((e) => (
                  <li key={e.id} onClick={() => onSelectEdge?.(e)}>
                    <strong>{e.predicate}</strong>
                    <span>
                      {nodeLabel(e.subject)} → {nodeLabel(e.object)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
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
            型
            <Combobox value={type} onChange={setType} mode="class" />
            {fieldErrors.type && <span className="field-error">{fieldErrors.type}</span>}
          </label>
          <PropertyForm
            classId={type}
            values={properties}
            onChange={setProperties}
            errors={propertyFieldErrors}
          />
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
        title="Nodeの削除"
        message={`「${displayName}」を削除しますか？\n\nこのNodeに接続されているRelationshipも削除されます。`}
        confirmLabel="削除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </div>
  );
}
