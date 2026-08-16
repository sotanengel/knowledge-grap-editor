import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Node, Relationship } from "../api/client";
import TypeSuggest from "./TypeSuggest";
import { slugFromLabel, uniqueId } from "../utils/idSlug";

const STEPS = ["起点", "関係", "終点", "確認"] as const;

function NodePicker({
  label,
  value,
  nodes,
  onChange,
  hint,
}: {
  label: string;
  value: string;
  nodes: Node[];
  onChange: (id: string) => void;
  hint?: string;
}) {
  const [query, setQuery] = useState("");
  const filtered = nodes.filter(
    (n) =>
      n.label.toLowerCase().includes(query.toLowerCase()) ||
      n.id.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <label>
      {label}
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="ノード名で検索..."
      />
      {hint && <span className="field-hint">{hint}</span>}
      <ul className="node-picker-list">
        {filtered.slice(0, 8).map((n) => (
          <li
            key={n.id}
            className={value === n.id ? "selected" : ""}
            onClick={() => onChange(n.id)}
          >
            <strong>{n.label}</strong>
            <span>{n.type} · {n.id}</span>
          </li>
        ))}
      </ul>
    </label>
  );
}

export default function RegisterEdgeWizard({ onCancel }: { onCancel?: () => void }) {
  const [step, setStep] = useState(0);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [relationships, setRelationships] = useState<Relationship[]>([]);
  const [edgeId, setEdgeId] = useState("");
  const [subject, setSubject] = useState("");
  const [predicate, setPredicate] = useState("");
  const [object, setObject] = useState("");
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [idWarning, setIdWarning] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    Promise.all([api.listNodes(), api.listRelationships()])
      .then(([n, r]) => {
        setNodes(n);
        setRelationships(r);
        setLoadError("");
      })
      .catch((e) => {
        setLoadError(e instanceof Error ? e.message : "ノード一覧の取得に失敗しました");
      });
  }, []);

  useEffect(() => {
    if (!subject || !predicate || !object) return;
    const base = slugFromLabel(`${subject}-${predicate}-${object}`.slice(0, 40));
    setEdgeId(base);
    setIdWarning("");
    api
      .listEdges()
      .then((edges) => {
        const ids = new Set(edges.map((e) => e.id));
        setEdgeId(uniqueId(base, ids));
      })
      .catch(() => {
        setIdWarning("重複チェックできませんでした。保存時に ID が重複する可能性があります。");
      });
  }, [subject, predicate, object]);

  const selectedRel = relationships.find((r) => r.id === predicate);
  const subjectNode = nodes.find((n) => n.id === subject);

  const canNext = (): boolean => {
    if (step === 0) return !!subject;
    if (step === 1) return !!predicate;
    if (step === 2) return !!object;
    return true;
  };

  const handleSave = async () => {
    setError("");
    try {
      await api.createEdge({ id: edgeId, subject, predicate, object, properties: {} });
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登録に失敗しました");
    }
  };

  if (saved) {
    return (
      <div className="wizard-success">
        <h3>関係の登録が完了しました</h3>
        <div className="btn-row">
          <button
            type="button"
            onClick={() => {
              setSaved(false);
              setStep(0);
              setSubject("");
              setPredicate("");
              setObject("");
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

      {loadError && <p className="error">{loadError}</p>}

      {step === 0 && (
        <section className="wizard-panel">
          <h3>起点ノードを選ぶ</h3>
          <NodePicker label="起点" value={subject} nodes={nodes} onChange={setSubject} />
        </section>
      )}

      {step === 1 && (
        <section className="wizard-panel">
          <h3>関係を選ぶ</h3>
          {subjectNode && (
            <p className="hint">
              起点: {subjectNode.label} ({subjectNode.type})
            </p>
          )}
          <label>
            関係
            <TypeSuggest
              value={predicate}
              onChange={setPredicate}
              mode="relationship"
              placeholder="関係を検索..."
            />
          </label>
          {selectedRel && selectedRel.domain.length > 0 && (
            <p className="field-hint">想定される起点の型: {selectedRel.domain.join(", ")}</p>
          )}
        </section>
      )}

      {step === 2 && (
        <section className="wizard-panel">
          <h3>終点ノードを選ぶ</h3>
          {selectedRel?.range.length ? (
            <NodePicker
              label="終点"
              value={object}
              nodes={nodes.filter((n) => selectedRel.range.includes(n.type))}
              onChange={setObject}
              hint={`推奨される型: ${selectedRel.range.join(", ")}`}
            />
          ) : (
            <NodePicker label="終点" value={object} nodes={nodes} onChange={setObject} />
          )}
        </section>
      )}

      {step === 3 && (
        <section className="wizard-panel">
          <h3>確認</h3>
          <dl className="confirm-list">
            <dt>ID</dt>
            <dd>{edgeId}</dd>
            <dt>起点</dt>
            <dd>{subject}</dd>
            <dt>関係</dt>
            <dd>{predicate}</dd>
            <dt>終点</dt>
            <dd>{object}</dd>
          </dl>
          {idWarning && <p className="warning">{idWarning}</p>}
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
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            キャンセル
          </button>
        )}
      </div>
    </div>
  );
}
