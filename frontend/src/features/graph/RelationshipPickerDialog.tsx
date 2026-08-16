import { useEffect, useMemo, useState } from "react";
import type { Node, Relationship } from "../../api/client";
import Combobox from "../../components/ui/Combobox";
import { filterRelationshipsByNodes } from "../../utils/graphValidation";

interface Props {
  open: boolean;
  sourceNode: Node;
  targetNode: Node;
  relationships: Relationship[];
  error?: string;
  onConfirm: (predicate: string) => void;
  onCancel: () => void;
}

export default function RelationshipPickerDialog({
  open,
  sourceNode,
  targetNode,
  relationships,
  error,
  onConfirm,
  onCancel,
}: Props) {
  const candidates = useMemo(
    () => filterRelationshipsByNodes(sourceNode, targetNode, relationships),
    [sourceNode, targetNode, relationships],
  );
  const [predicate, setPredicate] = useState("");

  useEffect(() => {
    if (!open) return;
    setPredicate(candidates.length === 1 ? candidates[0].id : "");
  }, [open, candidates]);

  if (!open) return null;

  const filterIds = new Set(candidates.map((r) => r.id));

  return (
    <div className="modal-overlay" role="presentation" onClick={onCancel}>
      <div
        className="modal-dialog relationship-picker-dialog"
        role="dialog"
        aria-labelledby="relationship-picker-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="relationship-picker-title">Relationshipを作成</h3>
        <p>
          <strong>{sourceNode.label}</strong> → <strong>{targetNode.label}</strong>
        </p>

        {candidates.length === 0 ? (
          <p className="error">
            このノードの組み合わせで使用できる Relationship がありません（domain/range
            不一致）。
          </p>
        ) : (
          <label>
            Relationship
            <Combobox
              value={predicate}
              onChange={setPredicate}
              mode="relationship"
              placeholder="関係を選択..."
              filterIds={filterIds}
            />
          </label>
        )}

        {error && <p className="error">{error}</p>}

        <div className="btn-row">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            キャンセル
          </button>
          <button
            type="button"
            disabled={candidates.length === 0 || !predicate}
            onClick={() => onConfirm(predicate)}
          >
            作成
          </button>
        </div>
      </div>
    </div>
  );
}
