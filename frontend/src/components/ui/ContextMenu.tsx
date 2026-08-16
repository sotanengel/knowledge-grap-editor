interface Props {
  x: number;
  y: number;
  items: Array<{ label: string; action: () => void; danger?: boolean }>;
  onClose: () => void;
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  return (
    <>
      <div className="modal-backdrop" style={{ background: "transparent" }} onClick={onClose} />
      <div className="context-menu" style={{ left: x, top: y }} data-testid="context-menu">
        {items.map((item) => (
          <button
            key={item.label}
            type="button"
            className={item.danger ? "danger" : ""}
            onClick={() => {
              item.action();
              onClose();
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
    </>
  );
}
