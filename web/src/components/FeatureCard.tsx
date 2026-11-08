import { useState } from "react";
import { request } from "../api/invoices";
import { Why } from "./Why";
import { Chip, DataTable, type ChipTone } from "./ui";

type Tag = "OBSERVED" | "ESTIMATED" | "SIMULATED" | "HYPOTHETICAL";

export interface DetailRow {
  date: string | null;
  label: string;
  bar: { value: number; max: number } | null;
  bar_text: string;
  note: string;
  tone: "check" | "muted";
  value: number | null;
  unit: string;
}

export interface Details {
  summary: string;
  info: string;
  columns: string[];
  rows: DetailRow[];
}

export interface Card {
  id: string;
  title: string;
  status: "Check this" | "Worth a check" | "Good" | "Not enough data";
  headline: string;
  example_line: string;
  explanation: string;
  reasoning: { title: string; text: string }[];
  example: { site: string | null; device: string | null; result: string; bars: { label: string; value: number; unit: string }[] } | null;
  evidence: { tag: Tag; range: string | null; confidence: "High" | "Medium" | "Low"; pickups_used: number; data_used: string; neutrality_note: string };
  actions: string[];
  advanced: { formula: string; columns: string[]; rows: (string | number | null)[][] };
  details: Details;
  decision: "prepare" | "not_now" | null;
  decision_id: string | null;
  rank: number;
}

const BADGE: Record<Card["status"], ChipTone> = {
  "Check this": "check",
  "Worth a check": "check",
  Good: "good",
  "Not enough data": "neutral",
};


function draft(c: Card) {
  return [`Proposal: ${c.title}`, c.headline, c.example_line, c.evidence.neutrality_note, "Could we discuss this?"]
    .filter(Boolean)
    .join("\n\n");
}

export function FeatureCard({ card, endpoint }: { card: Card; endpoint: string }) {
  const [decision, setDecision] = useState(card.decision);
  const [decisionId, setDecisionId] = useState(card.decision_id);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [more, setMore] = useState(false);
  const e = card.evidence;

  const act = async (fn: () => Promise<void>) => {
    setBusy(true);
    setFailed(false);
    try {
      await fn();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const decide = (d: "prepare" | "not_now") =>
    act(async () => {
      const saved = await request<{ decision_id: string }>(`${endpoint}/${encodeURIComponent(card.id)}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: d }),
      });
      setDecision(d);
      setDecisionId(saved.decision_id);
    });

  const undo = () =>
    act(async () => {
      if (!decisionId) return;
      await request(`/api/decisions/${encodeURIComponent(decisionId)}/undo`, { method: "POST" });
      setDecision(null);
      setDecisionId(null);
    });

  return (
    <section className="fcard" aria-labelledby={`t-${card.id}`}>
      <header className="fcard-head">
        <h2 id={`t-${card.id}`}>{card.title}</h2>
        <Chip tone={BADGE[card.status]}>{card.status}</Chip>
      </header>
      <p className="fcard-headline">{card.headline}</p>
      {card.example_line && <p className="muted fcard-example">{card.example_line}</p>}
      <div className="fcard-actions">
        {card.actions.length > 0 && decision === null && (
          <>
            <button type="button" className="btn btn-primary" disabled={busy} onClick={() => decide("prepare")}>
              Prepare proposal
            </button>
            <button type="button" className="btn btn-outline" disabled={busy} onClick={() => decide("not_now")}>
              Not now
            </button>
          </>
        )}
        {decision && <span className="note">{decision === "prepare" ? "Proposal prepared" : "Not now"}</span>}
        <Why
          label={card.title}
          info={{
            what: e.neutrality_note,
            reason: null,
            source: `${e.data_used} (${e.pickups_used} pickups)`,
            confidence: e.confidence.toLowerCase() as "high" | "medium" | "low",
            evidence: e.tag.toLowerCase() as "observed" | "estimated" | "simulated" | "hypothetical",
          }}
        />
        <button type="button" className="link" aria-expanded={more} onClick={() => setMore(!more)}>
          Details
        </button>
        {decisionId && (
          <button type="button" className="link" disabled={busy} onClick={undo}>
            Undo
          </button>
        )}
      </div>
      {failed && <p className="note" role="alert">Could not save. Try again.</p>}

      {decision === "prepare" && (
        <div className="draft">
          <label className="label" htmlFor={`d-${card.id}`}>
            Draft proposal (copy and send it yourself if you agree)
          </label>
          <textarea id={`d-${card.id}`} readOnly value={draft(card)} rows={7} />
          <div className="draft-actions">
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => navigator.clipboard.writeText(draft(card)).then(() => setCopied(true), () => setCopied(false))}
            >
              Copy
            </button>
            <span className="note" aria-live="polite">{copied ? "Copied" : ""}</span>
          </div>
        </div>
      )}

      {more && <DetailsPanel card={card} />}
    </section>
  );
}

const whole = new Intl.NumberFormat("fi-FI", { maximumFractionDigits: 0 });
const shortDate = (iso: string | null) =>
  iso ? new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "";

function DetailsPanel({ card }: { card: Card }) {
  const [all, setAll] = useState(false);
  const d = card.details;
  const rows = all ? d.rows : d.rows.slice(0, 4);
  return (
    <div className="details-panel">
      <p className="details-summary">
        {d.summary}
        <Why
          label={`${card.title} calculation`}
          info={{
            what: d.info,
            reason: null,
            source: card.evidence.data_used,
            confidence: card.evidence.confidence.toLowerCase() as "high" | "medium" | "low",
            evidence: card.evidence.tag.toLowerCase() as "observed" | "estimated" | "simulated" | "hypothetical",
          }}
        />
      </p>
      {d.rows.length > 0 && (
        <DataTable className="details-table">
          <table>
            <thead>
              <tr>
                {d.columns.map((c, i) => (
                  <th key={`${c}-${i}`} scope="col" className={i === 3 ? "num" : undefined}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="muted">{shortDate(r.date)}</td>
                  <td className="strong-text">{r.label}</td>
                  <td>
                    <div className="load">
                      {r.bar && (
                        <span className="load-track" aria-hidden="true">
                          <span className="load-fill" style={{ width: `${Math.min(100, (r.bar.value / r.bar.max) * 100)}%` }} />
                        </span>
                      )}
                      <span className="load-text">{r.bar_text}</span>
                    </div>
                    {r.note &&
                      (r.tone === "check" ? (
                        <Chip tone="check">{r.note}</Chip>
                      ) : (
                        <span className="sub-small">{r.note}</span>
                      ))}
                  </td>
                  <td className="num amount">
                    {r.value === null ? "–" : `${r.value > 0 && r.unit === "€" && card.id === "site_checks.shared_split" ? "+" : ""}${whole.format(r.value)} ${r.unit}`}
                  </td>
                </tr>
              ))}
            </tbody>
            {d.rows.length > 4 && !all && (
              <tfoot>
                <tr>
                  <td colSpan={4}>
                    <button type="button" className="link show-all" onClick={() => setAll(true)}>
                      Show all {d.rows.length}
                    </button>
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </DataTable>
      )}
    </div>
  );
}
