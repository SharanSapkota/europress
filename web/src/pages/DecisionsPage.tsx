import { Fragment, useEffect, useState } from "react";
import { getDecisions, undoDecision, type DecisionEntry } from "../api/decisions";
import { Chip, DataTable, FootNote, PageTitle, TableHeader } from "../components/ui";

const MONTHS = 3;

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: DecisionEntry[] };

const date = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const time = (iso: string) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

function Trail({ boxes }: { boxes: DecisionEntry["trail"] }) {
  return (
    <ol className="trail-boxes">
      {boxes.map((b, i) => (
        <li key={b.label} className="trail-step">
          {i > 0 && (
            <span className="trail-arrow" aria-hidden="true">
              →
            </span>
          )}
          <span className="trail-box">
            <span className="trail-label">{b.label}</span>
            <span className="trail-value">{b.value}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export function DecisionsPage() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getDecisions(MONTHS)
      .then((data) => {
        if (!live) return;
        setLoad({ state: "ready", data });
        setOpen((o) => o ?? data.find((e) => e.trail.length > 0 && e.decision !== "undo" && !e.undone)?.decision_id ?? null);
      })
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [attempt]);

  const undo = async (id: string) => {
    setBusy(true);
    try {
      await undoDecision(id);
      setAttempt((a) => a + 1);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageTitle
        title="Decisions"
        subtitle="Every suggestion you approved or declined, and what it was based on. Nothing is sent without you."
        context=""
      />
      {load.state === "loading" && <p className="status-text" role="status">Loading</p>}
      {load.state === "failed" && (
        <div className="status-text" role="alert">
          <p>Could not load. Try again.</p>
          <button type="button" className="btn btn-outline" onClick={() => setAttempt((a) => a + 1)}>
            Try again
          </button>
        </div>
      )}
      {load.state === "ready" &&
        (load.data.length === 0 ? (
          <p className="status-text">No decisions yet.</p>
        ) : (
          <DataTable>
            <table className="decisions-table">
              <TableHeader cells={["When", "Item", "Suggestion", "Your decision", <span className="visually-hidden">Action</span>]} />
              <tbody>
                {load.data.map((e) => {
                  const expanded = open === e.decision_id;
                  const active = e.decision !== "undo" && !e.undone;
                  return (
                    <Fragment key={e.decision_id}>
                      <tr className={`row${e.undone || e.decision === "undo" ? " is-past" : ""}${expanded ? " is-open" : ""}`}>
                        <td>
                          <span className="cell-date">{date(e.created_at)}</span>
                          <span className="sub-small">{time(e.created_at)}</span>
                        </td>
                        <td>
                          <span className="cell-title">{e.title}</span>
                          {e.detail && <span className="sub-small">{e.detail}</span>}
                        </td>
                        <td className="cell-text">{e.suggestion_text}</td>
                        <td>
                          <Chip tone={e.undone ? "neutral" : e.chip_tone}>{e.undone ? `${e.chip} · undone` : e.chip}</Chip>
                        </td>
                        <td className="action">
                          {expanded && active ? (
                            <button type="button" className="link-small" disabled={busy} onClick={() => undo(e.decision_id)}>
                              Undo<span className="visually-hidden"> {e.chip} for {e.title}</span>
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="link-small link-chevron"
                              aria-expanded={expanded}
                              onClick={() => setOpen(expanded ? null : e.decision_id)}
                            >
                              {expanded ? "Hide" : "Show"} <span aria-hidden="true">›</span>
                            </button>
                          )}
                        </td>
                      </tr>
                      {expanded && (
                        <tr className="trail-row">
                          <td colSpan={5}>
                            {e.trail.length ? (
                              <Trail boxes={e.trail} />
                            ) : (
                              <p className="sub-small trail-empty">{e.suggestion.text ?? "No evidence stored for this entry."}</p>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </DataTable>
        ))}
      <FootNote>Every decision is saved with time and user. Undo adds a new entry and keeps the old one. Demo data.</FootNote>
    </>
  );
}
