import { useRef, useState } from "react";
import { Link } from "react-router";
import type { Decision, LinePart } from "../api/invoices";
import { eur, qty } from "../format";
import type { TableRow } from "./ComparisonTable";
import { Why } from "./Why";

interface Props {
  row: TableRow;
  onDecide: (id: string, decision: Decision) => Promise<void>;
}

const UNIT: Record<string, string> = { t: "t", km: "km", lift: "lift", event: "event", pct_of_base: "%" };

function partText(p: LinePart | null) {
  if (!p) return { amount: "Not on this invoice", detail: "" };
  if (p.unit === "pct_of_base") return { amount: eur(p.amount_cents), detail: `${qty(p.quantity)} % of ${eur(p.rate_cents ?? 0)}` };
  const unit = UNIT[p.unit ?? ""] ?? p.unit ?? "";
  const rate = p.rate_cents === null ? "" : ` × ${eur(p.rate_cents)}`;
  return { amount: eur(p.amount_cents), detail: `${qty(p.quantity)} ${unit}${rate}` };
}

function trailText(row: TableRow) {
  const t = row.trail;
  const lines = t.invoice_line_ids.length ? `invoice lines ${t.invoice_line_ids.join(", ")}` : "not on an invoice";
  return [
    t.pickup_id && `pickup ${t.pickup_id}`,
    t.operator_job_ref && `job ${t.operator_job_ref}`,
    t.pickup_id && (t.ticket_id ? `scale ticket ${t.ticket_id}` : "no scale ticket shared"),
    t.contract_version_id && `contract version ${t.contract_version_id}`,
    lines,
  ]
    .filter(Boolean)
    .join(" → ");
}

export function RowDetails({ row, onDecide }: Props) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [showDraft, setShowDraft] = useState(row.decision === "dispute_draft" || row.decision === "dispute_sent");
  const [copied, setCopied] = useState(false);
  const draftRef = useRef<HTMLTextAreaElement>(null);

  const decide = async (decision: Decision) => {
    setBusy(true);
    setFailed(false);
    try {
      await onDecide(row.id, decision);
      setShowDraft(decision !== "ok");
      if (decision === "dispute_draft") setTimeout(() => draftRef.current?.focus(), 0);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    if (!row.draft) return;
    try {
      await navigator.clipboard.writeText(row.draft);
    } catch {
      draftRef.current?.select();
      document.execCommand("copy");
    }
    setCopied(true);
  };

  return (
    <div className="details">
      <table className="lines">
        <thead>
          <tr>
            <th scope="col">Line</th>
            <th scope="col">Our invoice</th>
            <th scope="col">Operator invoice</th>
          </tr>
        </thead>
        <tbody>
          {row.weight && (
            <tr>
              <th scope="row">
                Weight
                <Why info={row.why.weight} label="weight" />
              </th>
              <td className="strong">{row.weight.ours}</td>
              <td className="strong">{row.weight.operator}</td>
            </tr>
          )}
          {row.lines.map((l, i) => {
            const ours = l.ours ? partText(l.ours) : { amount: "Not expected", detail: "" };
            const op = partText(l.operator);
            return (
              <tr key={`${l.line_type}-${i}`} className={l.status === "CHECK" ? "line-check" : undefined}>
                <th scope="row">
                  {l.label}
                  <Why info={l.why} label={l.label} />
                  {l.status === "CHECK" && <span className="sub">Check this</span>}
                </th>
                <td>
                  <span className="strong">{ours.amount}</span>
                  {ours.detail && <span className="sub">{ours.detail}</span>}
                </td>
                <td>
                  <span className="strong">{op.amount}</span>
                  {op.detail && <span className="sub">{op.detail}</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="details-grid">
        <div>
          <h3 className="label">Possible reason</h3>
          <p className="reason">{row.reason}</p>
          {row.causeText && (
            <p className="note cause">
              <span className="why-key">Likely source:</span> {row.causeText}
            </p>
          )}
          <h3 className="label">Where the numbers come from</h3>
          <dl className="sources">
            {row.sources.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
            <div>
              <dt>How sure</dt>
              <dd>{row.confidence}</dd>
            </div>
          </dl>
        </div>
        <div className="decide">
          <div className="buttons">
            <button type="button" className="btn btn-outline" disabled={busy} onClick={() => decide("ok")}>
              Mark as OK
            </button>
            <button type="button" className="btn btn-filled" disabled={busy || !row.draft} onClick={() => decide("dispute_draft")}>
              Prepare question
            </button>
          </div>
          <p className="note">Nothing is sent to the operator. You decide.</p>
          {row.decision && (
            <p className="note">
              You can undo this in <Link to="/decisions">Decisions</Link>.
            </p>
          )}
          {failed && <p className="note" role="alert">Could not save. Try again.</p>}
        </div>
      </div>

      <p className="note trail">
        <span className="why-key">Trail:</span> {trailText(row)}
      </p>

      {showDraft && row.draft && (
        <div className="draft">
          <label className="label" htmlFor={`draft-${row.id}`}>
            Draft question (copy and send it yourself if you agree)
          </label>
          <textarea id={`draft-${row.id}`} ref={draftRef} readOnly value={row.draft} rows={10} />
          <div className="draft-actions">
            <button type="button" className="btn btn-outline" onClick={copy}>
              Copy
            </button>
            {row.decision === "dispute_sent" ? (
              <span className="note">Sent by you{row.decidedAt ? ` on ${row.decidedAt.slice(0, 10)}` : ""}.</span>
            ) : (
              <button type="button" className="btn btn-outline" disabled={busy} onClick={() => decide("dispute_sent")}>
                I sent it
              </button>
            )}
            <span className="note" aria-live="polite">{copied ? "Copied" : ""}</span>
          </div>
        </div>
      )}
    </div>
  );
}
