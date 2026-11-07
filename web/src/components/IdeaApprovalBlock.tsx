import { useRef, useState } from "react";
import { Link } from "react-router";
import type { OperatorDecision } from "../api/operators";
import { postIdeaDecision } from "../api/weightIdeas";

export function IdeaApprovalBlock({
  itemId,
  customerId,
  suggestion,
  reason,
  trailText,
  initialDecision,
  initialDraft,
}: {
  itemId: string;
  customerId: string;
  suggestion: string;
  reason: string;
  trailText: string;
  initialDecision: OperatorDecision | null;
  initialDraft: string | null;
}) {
  const [decision, setDecision] = useState<OperatorDecision | null>(initialDecision);
  const [draft, setDraft] = useState<string | null>(initialDraft);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  const draftRef = useRef<HTMLTextAreaElement>(null);

  const decide = async (d: OperatorDecision) => {
    setBusy(true);
    setFailed(false);
    try {
      const saved = await postIdeaDecision(itemId, d, customerId);
      setDecision(d);
      setDraft(saved.draft);
      if (d === "prepare") setTimeout(() => draftRef.current?.focus(), 0);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!draft) return;
    try {
      await navigator.clipboard.writeText(draft);
    } catch {
      draftRef.current?.select();
      document.execCommand("copy");
    }
    setCopied(true);
  };

  return (
    <div className="details">
      <p className="reason">
        <strong className="strong">Suggested proposal:</strong> {suggestion}
      </p>
      <p className="reason">{reason}</p>
      <p className="note">
        <strong className="strong">Traceability trail:</strong> {trailText}
      </p>
      <div style={{ marginTop: "16px" }}>
        {decision && (
          <p className="note" style={{ marginBottom: "8px" }}>
            {decision === "not_now" ? "You chose not now. " : "Proposal prepared. "}
            You can undo this in <Link to="/decisions">Decisions</Link>.
          </p>
        )}
        {decision !== "not_now" && (
          <div className="buttons">
            <button type="button" className="btn btn-filled" disabled={busy} onClick={() => decide("prepare")}>
              Prepare proposal
            </button>
            <button type="button" className="btn btn-outline" disabled={busy} onClick={() => decide("not_now")}>
              Not now
            </button>
          </div>
        )}
        {failed && (
          <p className="note" role="alert">
            Could not save decision. Try again.
          </p>
        )}
        {decision === "prepare" && draft && (
          <div className="draft">
            <label className="label" htmlFor={`draft-${itemId}`}>
              Draft proposal (human review required — nothing is sent automatically)
            </label>
            <textarea id={`draft-${itemId}`} ref={draftRef} readOnly value={draft} rows={7} />
            <div className="draft-actions">
              <button type="button" className="btn btn-outline" onClick={copy}>
                Copy
              </button>
              <span className="note" aria-live="polite">
                {copied ? "Copied" : ""}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
