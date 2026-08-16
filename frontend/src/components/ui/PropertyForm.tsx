import { useEffect, useState } from "react";
import { api, PropertyDef } from "../../api/client";

interface Props {
  classId: string;
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
  readOnly?: boolean;
  errors?: Record<string, string>;
}

function inferInputType(prop: PropertyDef): string {
  const range = prop.range.join(" ").toLowerCase();
  if (range.includes("boolean")) return "checkbox";
  if (range.includes("integer") || range.includes("number")) return "number";
  if (range.includes("date")) return "date";
  if (range.includes("uri") || range.includes("url")) return "url";
  return "text";
}

export default function PropertyForm({
  classId,
  values,
  onChange,
  readOnly = false,
  errors = {},
}: Props) {
  const [properties, setProperties] = useState<PropertyDef[]>([]);
  const [error, setError] = useState("");
  const [extraKeys, setExtraKeys] = useState<string[]>([]);

  useEffect(() => {
    if (!classId) {
      setProperties([]);
      return;
    }
    api
      .getClassProperties(classId)
      .then(setProperties)
      .catch((e) => setError(e instanceof Error ? e.message : "属性の取得に失敗しました"));
  }, [classId]);

  const updateField = (propId: string, value: string) => {
    onChange({ ...values, [propId]: value });
  };

  const knownIds = new Set([...properties.map((p) => p.id), ...extraKeys]);
  const adHocEntries = Object.entries(values).filter(([k]) => !knownIds.has(k));

  if (!classId && Object.keys(values).length === 0) {
    return <p className="hint">型を選択すると属性フィールドが表示されます。</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  const addProperty = () => {
    const key = `property_${extraKeys.length + 1}`;
    setExtraKeys([...extraKeys, key]);
    onChange({ ...values, [key]: "" });
  };

  return (
    <div className="property-fields" data-testid="property-form">
      {properties.map((prop) => {
        const inputType = inferInputType(prop);
        const val = values[prop.id] ?? "";
        if (readOnly) {
          return (
            <div key={prop.id} className="inspector-field">
              <label>{prop.label}{prop.required && " *"}</label>
              <div className="value">{val || "—"}</div>
            </div>
          );
        }
        if (inputType === "checkbox") {
          return (
            <label key={prop.id}>
              {prop.label}
              {prop.required && <span className="required"> *</span>}
              <input
                type="checkbox"
                checked={val === "true"}
                onChange={(e) => updateField(prop.id, e.target.checked ? "true" : "false")}
              />
              {errors[prop.id] && <span className="field-error">{errors[prop.id]}</span>}
            </label>
          );
        }
        return (
          <label key={prop.id}>
            {prop.label}
            {prop.required && <span className="required"> *</span>}
            <input
              type={inputType}
              value={val}
              onChange={(e) => updateField(prop.id, e.target.value)}
              placeholder={prop.description || prop.id}
            />
            {prop.description && <span className="field-hint">{prop.description}</span>}
            {errors[prop.id] && <span className="field-error">{errors[prop.id]}</span>}
          </label>
        );
      })}
      {!readOnly && (
        <>
          {adHocEntries.map(([k, v]) => (
            <label key={k}>
              {k}
              <input value={v} onChange={(e) => updateField(k, e.target.value)} />
            </label>
          ))}
          <button type="button" className="btn-secondary" onClick={addProperty}>
            + Propertyを追加
          </button>
        </>
      )}
      {readOnly &&
        adHocEntries.map(([k, v]) => (
          <div key={k} className="inspector-field">
            <label>{k}</label>
            <div className="value">{v}</div>
          </div>
        ))}
      {properties.length === 0 && !readOnly && classId && (
        <p className="hint">この型に定義された属性はありません。</p>
      )}
    </div>
  );
}
