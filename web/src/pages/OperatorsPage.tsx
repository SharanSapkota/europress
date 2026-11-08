import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { getOperators, postOperatorDecision, type OperatorCard, type Operators } from "../api/operators";
import { MessageModal } from "../components/MessageModal";
import { Chip, FootNote, InfoIcon, PageTitle } from "../components/ui";
import { month } from "../format";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Operators };

const PERIOD_TEXT: Record<string, string> = { "3m": "last 3 months", all: "all months", custom: "chosen months" };

export function OperatorsPage() {
  const [params, setParams] = useSearchParams();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [months, setMonths] = useState<string[]>([]);
  const [attempt, setAttempt] = useState(0);
  const [asking, setAsking] = useState<OperatorCard | null>(null);
  const mode = params.get("from") ? "custom" : params.get("period") ?? "3m";
  const query = new URLSearchParams(params);
  if (!query.get("period") && !query.get("from")) query.set("period", "3m");
  if (query.get("from")) query.delete("period");
  const q = query.toString();

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getOperators(q)
      .then((data) => {
        if (!live) return;
        setMonths(data.options.months);
        setLoad({ state: "ready", data });
      })
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [q, attempt]);

  const setMode = (value: string) => {
    const next = new URLSearchParams();
    if (value === "custom" && months.length) {
      next.set("from", months[Math.max(0, months.length - 3)]);
      next.set("to", months[months.length - 1]);
    } else if (value !== "3m") next.set("period", value);
    setParams(next);
  };
  const setRange = (key: "from" | "to", value: string) => {
    const next = new URLSearchParams(params);
    next.set(key, value);
    setParams(next);
  };

  const decide = async (op: OperatorCard, decision: "prepare" | "not_now", message?: string) => {
    await postOperatorDecision(op.operator_id, decision, q, message);
    setAttempt((a) => a + 1);
  };

  return (
    <>
      <PageTitle
        title="Operators"
        subtitle={`How your waste operators perform · ${PERIOD_TEXT[mode] ?? "last 3 months"}`}
        context=""
        right={
          <div className="period-filter">
            <label className="month-select">
              <span className="label">Period</span>
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="3m">Last 3 months</option>
                <option value="all">All</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            {mode === "custom" && (
              <>
                <label className="month-select">
                  <span className="label">From</span>
                  <select value={params.get("from") ?? ""} onChange={(e) => setRange("from", e.target.value)}>
                    {months.map((m) => (
                      <option key={m} value={m}>
                        {month(m)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="month-select">
                  <span className="label">To</span>
                  <select value={params.get("to") ?? ""} onChange={(e) => setRange("to", e.target.value)}>
                    {months.map((m) => (
                      <option key={m} value={m}>
                        {month(m)}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            )}
          </div>
        }
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
        (load.data.operators.length === 0 ? (
          <p className="status-text">No pickups by an operator in this period.</p>
        ) : (
          <div className="op-grid">
            {load.data.operators.map((op) => (
              <OperatorCardView key={op.operator_id} op={op} onPrepare={() => setAsking(op)} onNotNow={() => decide(op, "not_now")} />
            ))}
          </div>
        ))}
      {asking && (
        <MessageModal
          id={asking.operator_id}
          title="Prepare request"
          sub={`${asking.name} · ${asking.suggestion.replace(/\.$/, "")}`}
          message={asking.request_draft ?? ""}
          subject={`${asking.suggestion.replace(/\.$/, "")}`}
          onClose={() => setAsking(null)}
          onSave={(m) => decide(asking, "prepare", m)}
        />
      )}
      <FootNote>Suggestions only. Nothing is sent without your approval. Operator names are fictional. Demo data.</FootNote>
    </>
  );
}

function OperatorCardView({ op, onPrepare, onNotNow }: { op: OperatorCard; onPrepare: () => void; onNotNow: () => void }) {
  const check = op.status === "CHECK";
  const act = op.suggested_action !== "NONE";
  const name = op.name.replace(/\s*\(fictional\)$/i, "");
  return (
    <section className={act ? "card op-card is-check" : "card op-card"} aria-labelledby={`op-${op.operator_id}`}>
      <header className="op-head">
        <div>
          <h2 id={`op-${op.operator_id}`} className="op-name">
            {name}
          </h2>
          <p className="op-sub">
            {op.materials.join(", ") || "No contract"} · {op.pickups} {op.pickups === 1 ? "pickup" : "pickups"}
          </p>
        </div>
        <Chip tone={check ? "check" : "good"}>{check ? "Check" : "Good"}</Chip>
      </header>
      <dl className="op-rows">
        {op.measures.map((m) => (
          <div key={m.key} className="op-row">
            <dt>{m.label}</dt>
            <dd className="op-value">
              {m.value}
              {m.key === "tickets_shared" && <InfoIcon info={m.why} label={m.label} />}
            </dd>
            <dd>
              <Chip tone={m.status === "CHECK" ? "check" : "good"}>{m.status === "CHECK" ? "Check" : "Good"}</Chip>
            </dd>
          </div>
        ))}
      </dl>
      <div className={act ? "op-suggest is-check" : "op-suggest"}>
        <p className="section-label">Suggested</p>
        <p className="op-suggest-title">{act ? op.suggestion : "No action needed."}</p>
        {act && <p className="op-suggest-why">{op.why}</p>}
        {act &&
          (op.decision ? (
            <p className="sub-small">{op.decision === "prepare" ? "Request prepared. Nothing sent." : "Not now."}</p>
          ) : (
            <div className="op-actions">
              <button type="button" className="btn btn-primary" onClick={onPrepare}>
                Prepare request
              </button>
              <button type="button" className="btn btn-outline" onClick={onNotNow}>
                Not now
              </button>
            </div>
          ))}
      </div>
    </section>
  );
}
