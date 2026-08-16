import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import PropertyFields from "./PropertyFields";
import TypeSuggest from "./TypeSuggest";
import { slugFromLabel, uniqueId } from "../utils/idSlug";

const STEPS = ["名前", "型", "属性", "確認"] as const;

export default function RegisterNodeWizard({ onCancel }: { onCancel?: () => void }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [label, setLabel] = useState("");
  const [nodeId, setNodeId] = useState("");
  const [showIdEdit, setShowIdEdit] = useState(false);
  const [type, setType] = useState("");
  const [properties, setProperties] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [idWarning, setIdWarning] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!label.trim() || showIdEdit) return;
    const base = slugFromLabel(label);
    setNodeId(base);
    setIdWarning("");
    api
      .listNodes()
      .then((nodes) => {
        const ids = new Set(nodes.map((n) => n.id));
        setNodeId(uniqueId(base, ids));
      })
      .catch(() => {
        setIdWarning("重複チェックできませんでした。保存時に ID が重複する可能性があります。");
      });
  }, [label, showIdEdit]);

  const canNext = (): boolean => {
    if (step === 0) return label.trim().length > 0;
    if (step === 1) return type.trim().length > 0;
    return true;
  };

  const handleSave = async () => {
    setError("");
    try {
      const props = { ...properties };
      if (!props.name && label) props.name = label;
      await api.createNode({ id: nodeId, label, type, properties: props });
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登録に失敗しました");
    }
  };

  if (saved) {
    return (
      <div className="wizard-success">
        <h3>登録が完了しました</h3>
        <p>
          「{label}」を {type} として登録しました。
        </p>
        <div className="btn-row">
          <button
            type="button"
            onClick={() => {
              setSaved(false);
              setStep(0);
              setLabel("");
              setNodeId("");
              setType("");
              setProperties({});
              setIdWarning("");
            }}
          >
            続けて登録
          </button>
          <Link to="/browse" className="btn-link">
            閲覧で見る
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="wizard">
      <ol className="wizard-steps">
        {STEPS.map((name, i) => (
          <li key={name} className={i === step ? "active" : i < step ? "done" : ""}>
            {name}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <section className="wizard-panel">
          <h3>名前を入力</h3>
          <p className="hint">「Apple」「山田太郎」など、わかりやすい名前を入力してください。</p>
          <label>
            名前
            <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="例: Apple" />
          </label>
          {!showIdEdit ? (
            <p className="id-preview">
              ID: <code>{nodeId || "..."}</code>{" "}
              <button type="button" className="link-btn" onClick={() => setShowIdEdit(true)}>
                詳細設定
              </button>
            </p>
          ) : (
            <label>
              ID（上級者向け）
              <input value={nodeId} onChange={(e) => setNodeId(e.target.value)} />
            </label>
          )}
          {idWarning && <p className="warning">{idWarning}</p>}
        </section>
      )}

      {step === 1 && (
        <section className="wizard-panel">
          <h3>型を選ぶ</h3>
          <p className="hint">日本語で検索できます（例: 会社、組織、スマホ）。</p>
          <label>
            型
            <TypeSuggest value={type} onChange={setType} placeholder="型を検索..." />
          </label>
        </section>
      )}

      {step === 2 && (
        <section className="wizard-panel">
          <h3>属性を入力</h3>
          <PropertyFields classId={type} values={properties} onChange={setProperties} />
        </section>
      )}

      {step === 3 && (
        <section className="wizard-panel">
          <h3>確認</h3>
          <dl className="confirm-list">
            <dt>名前</dt>
            <dd>{label}</dd>
            <dt>ID</dt>
            <dd>{nodeId}</dd>
            <dt>型</dt>
            <dd>{type}</dd>
            {Object.entries(properties)
              .filter(([, v]) => v)
              .map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
          </dl>
        </section>
      )}

      {error && <p className="error">{error}</p>}

      <div className="btn-row wizard-nav">
        {step > 0 && (
          <button type="button" onClick={() => setStep((s) => s - 1)}>
            戻る
          </button>
        )}
        {step < STEPS.length - 1 ? (
          <button type="button" disabled={!canNext()} onClick={() => setStep((s) => s + 1)}>
            次へ
          </button>
        ) : (
          <button type="button" onClick={handleSave}>
            登録する
          </button>
        )}
        <button type="button" className="secondary" onClick={() => (onCancel ? onCancel() : navigate("/register"))}>
          キャンセル
        </button>
      </div>
    </div>
  );
}
