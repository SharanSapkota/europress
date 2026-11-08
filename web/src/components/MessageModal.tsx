import { useRef, useState, type ReactNode } from "react";

export interface StripItem {
  label: string;
  value: string;
  check?: boolean;
}

interface Props {
  id: string;
  title: string;
  sub: string;
  strip?: StripItem[];
  message: string;
  subject: string;
  icon?: ReactNode;
  onClose: () => void;
  onSave: (message: string) => Promise<void>;
}

export function MessageModal({ id, title, sub, strip, message, subject, onClose, onSave }: Props) {
  const ref = useRef<HTMLDialogElement | null>(null);
  const [text, setText] = useState(message);
  const [busy, setBusy] = useState(false);
  const titleId = `modal-${id}`;
  const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(text)}`;
  const open = (node: HTMLDialogElement | null) => {
    ref.current = node;
    if (node && !node.open) node.showModal();
  };
  const save = async () => {
    setBusy(true);
    try {
      await onSave(text);
      ref.current?.close();
    } finally {
      setBusy(false);
    }
  };
  return (
    <dialog ref={open} className="modal" aria-labelledby={titleId} onClose={onClose}>
      <header className="modal-head">
        <div>
          <h2 id={titleId} className="modal-title">
            {title}
          </h2>
          <p className="modal-sub">{sub}</p>
        </div>
        <button type="button" className="modal-close" aria-label="Close" onClick={() => ref.current?.close()}>
          ×
        </button>
      </header>
      {strip && strip.length > 0 && (
        <dl className="modal-strip">
          {strip.map((s) => (
            <div key={s.label}>
              <dt>{s.label}</dt>
              <dd className={s.check ? "diff-check" : undefined}>{s.value}</dd>
            </div>
          ))}
        </dl>
      )}
      <div className="modal-body">
        <label className="label" htmlFor={`msg-${id}`}>
          Message (you can edit it)
        </label>
        <textarea id={`msg-${id}`} value={text} rows={8} onChange={(e) => setText(e.target.value)} />
        <div className="modal-actions">
          <a className="btn btn-primary" href={mailto} onClick={() => void save()} aria-disabled={busy}>
            <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M3 5h18v14H3zM3 6l9 7 9-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
            </svg>
            Open in email
          </a>
          <button type="button" className="btn btn-outline" disabled={busy} onClick={() => navigator.clipboard.writeText(text).finally(save)}>
            Copy
          </button>
          <p className="modal-note">Nothing is sent by Smart Weight. You send it yourself.</p>
        </div>
      </div>
    </dialog>
  );
}
