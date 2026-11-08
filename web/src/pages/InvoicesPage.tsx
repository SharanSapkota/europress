import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getComparison,
  getPeriods,
  postQuestion,
  type Comparison,
  type PickupComparison,
  type UnmatchedLine,
} from "../api/invoices";
import { ComparisonTable, type TableRow } from "../components/ComparisonTable";
import { TotalsStrip } from "../components/TotalsStrip";
import { FootNote, InfoLine, PageTitle, StatRow, StatTile } from "../components/ui";
import { month, t } from "../format";

const SOURCE_TEXT = { ticket: "scale ticket", invoice: "invoice quantity", device: "device estimate" } as const;
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
  return {
    id: r.pickup_id,
    date: r.date,
    material: r.material,
    ours: { amount: r.ours.amount_cents, note: r.ours_note, why: r.why.ours },
    operator: { amount: r.operator.amount_cents, note: r.billed_note },
    difference: r.difference_cents,
    status: r.status,
    view: r.view,
    reason: r.reason,
    shortReason: r.short_reason,
    confidence: r.ours.confidence,
    sources: sourceList(r.sources),
    weight: r.ours.weight_kg !== null || r.operator.billed_kg !== null
      ? { ours: ourWeight(r), operator: r.operator.billed_kg === null ? "Not billed by weight" : t(r.operator.billed_kg) }
      : null,
    lines: r.lines,
    decision: r.decision,
    disputedAt: r.disputed_at,
    causeText: r.cause_text,
    trail: r.trail,
    dispute: { invoiceId: r.invoice_ids[0] ?? null, message: r.dispute_message, pickup: true },
  };
}

function fromUnmatched(u: UnmatchedLine): TableRow {
  return {
    id: u.entity_id ?? u.label,
    date: u.service_date,
    material: null,
    ours: { amount: null, note: u.ours_note },
    operator: { amount: u.euros_at_stake_cents, note: u.billed_note },
    difference: u.euros_at_stake_cents,
    status: u.status,
    view: u.view,
    reason: u.reason,
    shortReason: u.short_reason,
    confidence: u.confidence,
    sources: sourceList(u.sources),
    weight: null,
    lines: [],
    decision: u.decision,
    disputedAt: u.disputed_at,
    causeText: u.cause_text,
    trail: u.trail,
    dispute: { invoiceId: u.invoice_id, message: u.dispute_message, pickup: false },
  };
}

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

function scopeText(data: Comparison) {
  const sites = plural(data.site_ids.length, "site", "sites");
  const ops = plural(data.operator_ids.length, "operator", "operators");
  return [data.customer_name, sites, ops].filter(Boolean).join(" · ");
}

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Comparison };

export function InvoicesPage() {
  const [periods, setPeriods] = useState<string[]>([]);
  const [period, setPeriod] = useState<string | null>(null);
  const [load, setLoad] = useState<Load>({ state: "loading" });
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

  const onQuestion = useCallback(async (row: TableRow, message: string) => {
    await postQuestion(row.id, message, row.dispute.pickup);
    setAttempt((a) => a + 1);
  }, []);

  const tables = useMemo(() => {
    if (load.state !== "ready") return null;
    const all = [...load.data.rows.map(fromPickup), ...load.data.unmatched_lines.map(fromUnmatched)]
      .sort((a, b) => (a.date ?? "").localeCompare(b.date ?? "") || a.id.localeCompare(b.id));
    const flagged = (r: TableRow) => r.view === "check" || r.view === "disputed";
    return { rows: all.filter(flagged), restRows: all.filter((r) => !flagged(r)) };
  }, [load]);

  return (
    <>
      <PageTitle
        title="Invoice comparison"
        subtitle="What each pickup should cost under your contract, next to what the operator billed."
        context={load.state === "ready" && load.data.period ? scopeText(load.data) : undefined}
        right={
          periods.length > 0 && (
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
          )
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

      {load.state === "ready" && tables && (
        tables.rows.length + tables.restRows.length === 0 ? (
          <p className="status-text">No invoices for this month.</p>
        ) : (
          <>
            <TotalsStrip totals={load.data.totals} why={load.data.why} />
            <StatRow>
              <StatTile label="To check" value={String(load.data.view_counts.check)} check={load.data.view_counts.check > 0} />
              <StatTile label="Disputed" value={String(load.data.view_counts.disputed)} />
              <StatTile label="Explained" value={String(load.data.view_counts.explained)} />
              <StatTile label="Match" value={String(load.data.view_counts.match)} />
            </StatRow>
            <InfoLine>A difference is not proof of a mistake. You decide what to do.</InfoLine>
            <ComparisonTable
              rows={tables.rows}
              restRows={tables.restRows}
              counts={{ match: load.data.view_counts.match, explained: load.data.view_counts.explained }}
              onQuestion={onQuestion}
            />
          </>
        )
      )}
      <FootNote>Suggestions only. Nothing is sent without your approval. Demo data, fictional customer.</FootNote>
    </>
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
    view_counts: { check: 0, disputed: 0, explained: 0, match: 0 },
    attention_count: 0,
    match_count: 0,
    line_counts: { MATCHED: 0, DUPLICATE: 0, NO_LIFT: 0 },
    unmatched_lines: [],
    rows: [],
  };
}
