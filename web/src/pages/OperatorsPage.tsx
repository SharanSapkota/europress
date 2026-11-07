import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { getOperators, postOperatorDecision, type OperatorCard, type OperatorDecision, type Operators } from "../api/operators";
import { Why } from "../components/Why";
import { eur } from "../format";

const PERIODS: [string, string][] = [
  ["all", "All months"],
  ["3m", "Last 3 months"],
  ["6m", "Last 6 months"],
  ["12m", "Last 12 months"],
];

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Operators };

export function OperatorsPage() {
  const [params, setParams] = useSearchParams();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [options, setOptions] = useState<Operators["options"] | null>(null);
  const [attempt, setAttempt] = useState(0);
  const query = params.toString();
  const period = params.get("period") ?? "all";

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getOperators(query)
      .then((data) => {
        if (!live) return;
        setOptions(data.options);
        setLoad({ state: "ready", data });
      })
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [query, attempt]);

  const choose = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === "customer_id") next.delete("site_id");
    setParams(next);
  };

  const customer = params.get("customer_id") ?? (load.state === "ready" ? load.data.customer_id ?? "" : "");

  return (
    <>
      <h1>Operators</h1>
      <p className="muted subtitle">
        How your waste operators perform · {PERIODS.find(([k]) => k === period)?.[1].toLowerCase() ?? "all months"}
      </p>

      {options && (
        <div className="filters">
          <label className="month-select">
            <span className="label">Customer</span>
            <select value={customer} onChange={(e) => choose("customer_id", e.target.value)}>
              <option value="all">All customers</option>
              {options.customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label className="month-select">
            <span className="label">Site</span>
            <select value={params.get("site_id") ?? ""} onChange={(e) => choose("site_id", e.target.value)}>
              <option value="">All sites</option>
              {options.sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
          <label className="month-select">
            <span className="label">Period</span>
            <select value={period} onChange={(e) => choose("period", e.target.value === "all" ? "" : e.target.value)}>
              {PERIODS.map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

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
          <p className="status-text">No pickups for this choice.</p>
        ) : (
          <>
            <div className="cards">
              {load.data.operators.map((op) => (
                <Card key={`${op.operator_id}-${query}`} op={op} query={query} />
              ))}
            </div>
            <p className="note">Suggestions only. Nothing is sent to the operator.</p>
          </>
        ))}
    </>
  );
}

function Card({ op, query }: { op: OperatorCard; query: string }) {
  const [decision, setDecision] = useState<OperatorDecision | null>(op.decision);
  const [draft, setDraft] = useState<string | null>(op.draft);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  const draftRef = useRef<HTMLTextAreaElement>(null);
  const titleId = `op-${op.operator_id}`;

  const decide = async (d: OperatorDecision) => {
    setBusy(true);
    setFailed(false);
    try {
      const saved = await postOperatorDecision(op.operator_id, d, query);
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
    <section className="card" aria-labelledby={titleId}>
      <header className="card-head">
        <h2 id={titleId}>{op.name}</h2>
        <span className="muted">{op.materials.join(", ")}</span>
      </header>
      <p className="muted card-scope">
        {op.enough_data ? `${op.pickups} pickups` : `Based on ${op.pickups} pickups, not sure yet`} ·{" "}
        {op.months === 1 ? "1 month" : `${op.months} months`}
      </p>
      <dl className="measures">
        {op.measures.map((m) => (
          <div key={m.key}>
            <dt>{m.label}</dt>
            <dd>
              <span className="strong-text">{m.value}</span>
              <Why info={m.why} label={`${m.label} for ${op.name}`} />
            </dd>
            <dd className={m.status === "GOOD" ? "word-good" : "word-check"}>{m.status === "GOOD" ? "Good" : "Check"}</dd>
          </div>
        ))}
      </dl>
      <div className="suggested">
        <p className="label">Suggested</p>
        <h3>{op.suggestion}</h3>
        <p>
          {op.why}
          <Why info={op.suggestion_why} label={`suggestion for ${op.name}`} />
        </p>
        {op.value_cents !== null && <p className="note">Expected value about {eur(op.value_cents)} (estimate).</p>}
        {op.suggested_action !== "NONE" && (
          <>
            {decision && (
              <p className="note">
                {decision === "not_now" ? "You chose not now. " : ""}You can undo this in <Link to="/decisions">Decisions</Link>.
              </p>
            )}
            {decision === "not_now" ? null : (
              <div className="buttons">
                <button type="button" className="btn btn-filled" disabled={busy} onClick={() => decide("prepare")}>
                  Prepare request
                </button>
                <button type="button" className="btn btn-outline" disabled={busy} onClick={() => decide("not_now")}>
                  Not now
                </button>
              </div>
            )}
            {failed && <p className="note" role="alert">Could not save. Try again.</p>}
            {decision === "prepare" && draft && (
              <div className="draft">
                <label className="label" htmlFor={`draft-${op.operator_id}`}>
                  Draft request (copy and send it yourself if you agree)
                </label>
                <textarea id={`draft-${op.operator_id}`} ref={draftRef} readOnly value={draft} rows={8} />
                <div className="draft-actions">
                  <button type="button" className="btn btn-outline" onClick={copy}>
                    Copy
                  </button>
                  <span className="note" aria-live="polite">{copied ? "Copied" : ""}</span>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
