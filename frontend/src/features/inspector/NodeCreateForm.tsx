import { useEffect, useMemo, useState } from "react";
import { api, OntologyClass, PropertyDef } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import PropertyForm from "../../components/ui/PropertyForm";
import { useToast } from "../../hooks/useToast";
import { propertyErrorsForForm, validateNode } from "../../utils/graphValidation";
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
  const [propertyDefs, setPropertyDefs] = useState<PropertyDef[]>([]);
  const [existingNodeIds, setExistingNodeIds] = useState<Set<string>>(new Set());
  const [classes, setClasses] = useState<OntologyClass[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    void api.listClasses().then(setClasses).catch(() => setClasses([]));
    void api.listNodes().then((nodes) => setExistingNodeIds(new Set(nodes.map((n) => n.id))));
  }, []);

  useEffect(() => {
    if (!label.trim()) return;
    const base = slugFromLabel(label);
    setNodeId(uniqueId(base, existingNodeIds));
  }, [label, existingNodeIds]);

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

  const propertyFieldErrors = useMemo(() => propertyErrorsForForm(fieldErrors), [fieldErrors]);

  const handleCreate = async () => {
    const props = { ...properties };
    if (description) props.description = description;
    if (!props.name) props.name = label;

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
      { id: nodeId, label, type, properties: props },
      defs,
      classList,
      { existingNodeIds },
    );
    if (!validation.valid) {
      setFieldErrors(validation.fieldErrors);
      setError("入力内容を確認してください");
      showToast("error", "入力内容を確認してください");
      return;
    }

    setError("");
    setFieldErrors({});
    setSaving(true);
    try {
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
        {fieldErrors.label && <span className="field-error">{fieldErrors.label}</span>}
      </label>
      <label>
        型
        <Combobox value={type} onChange={setType} mode="class" placeholder="型を検索..." />
        {fieldErrors.type && <span className="field-error">{fieldErrors.type}</span>}
      </label>
      <label>
        説明
        <input value={description} onChange={(e) => setDescription(e.target.value)} />
      </label>
      <label>
        ID
        <input value={nodeId} onChange={(e) => setNodeId(e.target.value)} />
        {fieldErrors.id && <span className="field-error">{fieldErrors.id}</span>}
      </label>
      <PropertyForm
        classId={type}
        values={properties}
        onChange={setProperties}
        errors={propertyFieldErrors}
      />
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
