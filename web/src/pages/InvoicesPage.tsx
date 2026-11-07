import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getComparison,
  getPeriods,
  postDecision,
  type Comparison,
  type Decision,
  type PickupComparison,
  type UnmatchedLine,
} from "../api/invoices";
import { ComparisonTable, type TableRow } from "../components/ComparisonTable";
import { TotalsStrip } from "../components/TotalsStrip";
import { month, t } from "../format";

const SOURCE_TEXT = { ticket: "weighbridge ticket", invoice: "invoice quantity", device: "device estimate" } as const;
const SOURCE_LABELS: Record<string, string> = {
  our_amount: "Our invoice",
  our_weight: "Our weight",
  operator_amount: "Operator invoice",
  billed_weight: "Billed weight",
  device_weight: "Device weight",
  grade: "Quality grade",
};

function sourceList(s: Record<string, string | null>): [string, string][] {
  return Object.entries(s)
    .filter((e): e is [string, string] => Boolean(e[1]))
    .map(([k, v]) => [SOURCE_LABELS[k] ?? k, v]);
}

function ourWeight(r: PickupComparison) {
  const { weight_kg, weight_source, range_kg } = r.ours;
  if (weight_kg === null || !weight_source) return "No weight";
  const range = range_kg ? ` ± ${t(range_kg)}` : "";
  return `${t(weight_kg)}${range}, ${SOURCE_TEXT[weight_source]}`;
}

function fromPickup(r: PickupComparison): TableRow {
  const billed = r.operator.billed_kg === null ? "No weight billed" : `${t(r.operator.billed_kg)} billed`;
  return {
    id: r.pickup_id,
    date: r.date,
    material: r.material,
    ours: { amount: r.ours.amount_cents, sub: ourWeight(r) },
    operator: { amount: r.operator.amount_cents, sub: r.lines.some((l) => l.operator) ? billed : "Not on the invoice" },
    difference: r.difference_cents,
    status: r.status,
    reason: r.reason,
    confidence: r.ours.confidence,
    sources: sourceList(r.sources),
    weight: r.ours.weight_kg !== null || r.operator.billed_kg !== null
      ? { ours: ourWeight(r), operator: r.operator.billed_kg === null ? "Not billed by weight" : t(r.operator.billed_kg) }
      : null,
    lines: r.lines,
    draft: r.draft_question,
    decision: r.decision,
    decidedAt: r.decided_at,
    why: r.why,
    causeText: r.cause_text,
    trail: r.trail,
  };
}

function fromUnmatched(u: UnmatchedLine): TableRow {
  return {
    id: u.entity_id ?? u.label,
    date: u.service_date,
    material: null,
    ours: { amount: null, sub: "No pickup found" },
    operator: { amount: u.euros_at_stake_cents, sub: u.label },
    difference: u.euros_at_stake_cents,
    status: u.status,
    reason: u.reason,
    confidence: u.confidence,
    sources: sourceList(u.sources),
    weight: null,
    lines: [],
    draft: u.draft_question,
    decision: u.decision,
    decidedAt: u.decided_at,
    why: { operator: u.why.amount, difference: u.why.amount },
    causeText: u.cause_text,
    trail: u.trail,
  };
}

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

function scopeText(data: Comparison) {
  const sites = data.site_ids.length === 1 ? data.site_ids[0] : plural(data.site_ids.length, "site", "sites");
  const ops = data.operator_ids.length === 1 ? `Operator: ${data.operator_ids[0]}` : plural(data.operator_ids.length, "operator", "operators");
  return `${month(data.period)} · ${sites} · ${ops}`;
}

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Comparison };

export function InvoicesPage() {
  const [periods, setPeriods] = useState<string[]>([]);
  const [period, setPeriod] = useState<string | null>(null);
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [decisions, setDecisions] = useState<Record<string, { decision: Decision; at: string }>>({});
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    (async () => {
      try {
        const list = periods.length ? periods : await getPeriods();
        if (!live) return;
        if (!periods.length) setPeriods(list);
        const p = period ?? list[list.length - 1];
        if (!p) {
          setLoad({ state: "ready", data: emptyComparison("") });
          return;
        }
        if (!period) setPeriod(p);
        const data = await getComparison(p);
        if (live) setLoad({ state: "ready", data });
      } catch {
        if (live) setLoad({ state: "failed" });
      }
    })();
    return () => {
      live = false;
    };
  }, [period, attempt]);

  const onDecide = useCallback(async (id: string, decision: Decision) => {
    const saved = await postDecision(id, decision);
    setDecisions((d) => ({ ...d, [id]: { decision, at: saved.created_at } }));
  }, []);

  const tables = useMemo(() => {
    if (load.state !== "ready") return null;
    const withDecision = (r: TableRow): TableRow => {
      const d = decisions[r.id];
      if (!d) return r;
      const status = d.decision === "dispute_sent" ? "DISPUTED" : r.status === "DISPUTED" ? "CHECK" : r.status;
      return { ...r, decision: d.decision, decidedAt: d.at, status };
    };
    const pickups = load.data.rows.map(fromPickup).map(withDecision);
    const unmatched = load.data.unmatched_lines.map(fromUnmatched).map(withDecision);
    const order = ["CHECK", "DISPUTED", "NO_DATA", "EXPLAINED"];
    const rows = [...pickups.filter((r) => r.status !== "MATCH"), ...unmatched].sort(
      (a, b) => order.indexOf(a.status) - order.indexOf(b.status) || (a.date ?? "").localeCompare(b.date ?? ""),
    );
    return { rows, matchRows: pickups.filter((r) => r.status === "MATCH") };
  }, [load, decisions]);

  return (
    <>
      <div className="title-row">
        <div>
          <h1>Invoice comparison</h1>
          {load.state === "ready" && load.data.period && <p className="muted">{scopeText(load.data)}</p>}
        </div>
        {periods.length > 0 && (
          <label className="month-select">
            <span className="label">Month</span>
            <select value={period ?? ""} onChange={(e) => setPeriod(e.target.value)}>
              {periods.map((p) => (
                <option key={p} value={p}>
                  {month(p)}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {load.state === "loading" && <p className="status-text" role="status">Loading</p>}

      {load.state === "failed" && (
        <div className="status-text" role="alert">
          <p>Could not load. Try again.</p>
          <button type="button" className="btn btn-outline" onClick={() => setAttempt((a) => a + 1)}>
            Try again
          </button>
        </div>
      )}

      {load.state === "ready" && tables && (
        tables.rows.length + tables.matchRows.length === 0 ? (
          <p className="status-text">No invoices for this month.</p>
        ) : (
          <>
            <TotalsStrip totals={load.data.totals} why={load.data.why} />
            <Summary data={load.data} />
            <ComparisonTable rows={tables.rows} matchRows={tables.matchRows} onDecide={onDecide} />
          </>
        )
      )}
    </>
  );
}

function Summary({ data }: { data: Comparison }) {
  const check = data.counts.CHECK + data.unmatched_lines.filter((u) => u.status === "CHECK").length;
  const disputed = data.counts.DISPUTED + data.unmatched_lines.filter((u) => u.status === "DISPUTED").length;
  const parts = [
    plural(check, "item to check", "items to check"),
    `${data.counts.EXPLAINED} explained`,
    `${data.counts.NO_DATA} without enough data`,
    ...(disputed ? [`${disputed} disputed`] : []),
  ];
  return (
    <div className="summary">
      <p className="summary-line">{check + disputed + data.counts.EXPLAINED + data.counts.NO_DATA === 0 ? "Everything matches." : `${parts.join(", ")}.`}</p>
      <p className="muted">
        We compare the invoice we calculate from your weights and contract with the invoice from your waste operator. A
        difference is not proof of a mistake.
      </p>
    </div>
  );
}

const NO_WHY = { what: "No invoices.", source: "Not enough data", confidence: "not enough data", reason: null, evidence: "estimated" } as const;

function emptyComparison(period: string): Comparison {
  return {
    period,
    tolerance_pct: 0,
    customer_name: null,
    site_ids: [],
    site_names: [],
    operator_ids: [],
    operator_names: [],
    why: { ours: NO_WHY, operator: NO_WHY, difference: NO_WHY },
    totals: { ours_cents: 0, operator_cents: 0, difference_cents: 0, unmatched_cents: 0, monthly_fixed_cents: 0 },
    counts: { MATCH: 0, CHECK: 0, EXPLAINED: 0, NO_DATA: 0, DISPUTED: 0 },
    line_counts: { MATCHED: 0, DUPLICATE: 0, NO_LIFT: 0 },
    unmatched_lines: [],
    rows: [],
  };
}
