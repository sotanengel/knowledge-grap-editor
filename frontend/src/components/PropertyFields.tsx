import { useEffect, useState } from "react";
import { api, PropertyDef } from "../api/client";

interface Props {
  classId: string;
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
}

export default function PropertyFields({ classId, values, onChange }: Props) {
  const [properties, setProperties] = useState<PropertyDef[]>([]);
  const [error, setError] = useState("");

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

  if (!classId) {
    return <p className="hint">型を選択すると属性フィールドが表示されます。</p>;
  }

  if (error) {
    return <p className="error">{error}</p>;
  }

  if (properties.length === 0) {
    return <p className="hint">この型に定義された属性はありません。</p>;
  }

  return (
    <div className="property-fields">
      {properties.map((prop) => (
        <label key={prop.id}>
          {prop.label}
          {prop.required && <span className="required"> *</span>}
          <input
            type="text"
            value={values[prop.id] ?? ""}
            onChange={(e) => updateField(prop.id, e.target.value)}
            placeholder={prop.description || prop.id}
          />
          {prop.description && <span className="field-hint">{prop.description}</span>}
        </label>
      ))}
    </div>
  );
}
