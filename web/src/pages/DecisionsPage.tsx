import { useEffect, useState } from "react";
import { getDecisions, undoDecision, type DecisionEntry } from "../api/decisions";

const MONTHS = 3;
const ACTION_TEXT: Record<string, string> = {
  CORRECT_LINE: "Ask to correct this line",
  REQUEST_TICKET: "Ask for the scale ticket",
  NONE: "No action",
  REQUEST_TICKETS: "Ask for the missing scale tickets",
  CORRECT_LINES: "Ask to correct the invoice lines",
  RENEGOTIATE: "Consider renegotiating the contract",
  TENDER: "Consider asking other operators for offers",
  PREPARE_WEIGHT_ACTION: "Prepare weight-based proposal",
};

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: DecisionEntry[] };

const when = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export function DecisionsPage() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  const undo = async (id: string) => {
    setBusy(id);
    try {
      await undoDecision(id);
      setAttempt((a) => a + 1);
    } finally {
      setBusy(null);
    }
  };

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getDecisions(MONTHS)
      .then((data) => live && setLoad({ state: "ready", data }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [attempt]);

  return (
    <>
      <h1>Decisions</h1>
      <p className="muted subtitle">Last {MONTHS} months, newest first</p>
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
          <div className="table-box">
            <table className="history">
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Item</th>
                  <th scope="col">Decision</th>
                  <th scope="col">Suggested action</th>
                  <th scope="col"><span className="visually-hidden">Undo</span></th>
                </tr>
              </thead>
              <tbody>
                {load.data.map((e) => (
                  <tr key={e.decision_id}>
                    <td className="muted">{when(e.created_at)}</td>
                    <td>{e.label}</td>
                    <td>
                      {e.text}
                      {e.undone && <span className="muted"> (undone)</span>}
                    </td>
                    <td className="muted">{ACTION_TEXT[e.suggestion.action ?? ""] ?? "–"}</td>
                    <td className="action">
                      {e.decision !== "undo" && !e.undone && (
                        <button type="button" className="link" disabled={busy !== null} onClick={() => undo(e.decision_id)}>
                          Undo<span className="visually-hidden"> {e.text} for {e.label}</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </>
  );
}
