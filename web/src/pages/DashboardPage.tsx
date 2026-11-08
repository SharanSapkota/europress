import { useEffect, useState } from "react";
import { Link } from "react-router";
import { request } from "../api/invoices";
import { useDashboard, type Dashboard, type Tile } from "../components/HeaderTools";
import { Card, FootNote, PageTitle, StatRow, StatTile, TotalsPanel } from "../components/ui";
import { eurWhole, month, signedWhole } from "../format";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Dashboard };

function show(t: Tile) {
  if (t.value === null) return "–";
  return t.unit === "×" ? `${t.value.toFixed(1)}×` : String(t.value);
}

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

export function DashboardPage() {
  const ctx = useDashboard();
  const [period, setPeriod] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [own, setOwn] = useState<Load | null>(null);

  useEffect(() => {
    if (!period) return;
    let live = true;
    setOwn({ state: "loading" });
    request<Dashboard>(`/api/dashboard?period=${encodeURIComponent(period)}`)
      .then((data) => live && setOwn({ state: "ready", data }))
      .catch(() => live && setOwn({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [period, attempt]);

  const load: Load = own ?? ctx.load;
  const data = load.state === "ready" ? load.data : null;
  const context = data?.customer_name
    ? [data.customer_name, plural(data.sites.length, "site", "sites"), plural(data.operator_count, "operator", "operators")].join(" · ")
    : undefined;

  return (
    <>
      <PageTitle
        title="Dashboard"
        context={context}
        right={
          data &&
          data.periods.length > 0 && (
            <label className="month-select">
              <span className="label">Month</span>
              <select value={period ?? data.period ?? ""} onChange={(e) => setPeriod(e.target.value)}>
                {data.periods.map((p) => (
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
          <button type="button" className="btn btn-outline" onClick={() => (period ? setAttempt((a) => a + 1) : ctx.retry())}>
            Try again
          </button>
        </div>
      )}
      {data && (
        <>
          {data.totals && (
            <TotalsPanel
              items={[
                { label: "Should cost (estimate)", value: eurWhole(data.totals.ours_cents), info: data.why.ours },
                { label: "Billed", value: eurWhole(data.totals.operator_cents), info: data.why.operator },
                { label: "Difference", value: signedWhole(data.totals.difference_cents), info: data.why.difference },
              ]}
            />
          )}
          <StatRow>
            {data.tiles.map((t) => (
              <StatTile key={t.key} label={t.label} value={show(t)} check={t.status === "CHECK"} to={t.link} />
            ))}
          </StatRow>
          {data.next_decision && (
            <Card className="next-card">
              <div>
                <h2 className="section-label">Next suggested decision</h2>
                <p className="next-sentence">{data.next_decision.sentence}</p>
                <p className="next-estimate">{data.next_decision.estimate}</p>
              </div>
              <Link to={data.next_decision.link} className="btn btn-primary">
                Review
              </Link>
            </Card>
          )}
        </>
      )}
      <FootNote>Suggestions only. Nothing is sent without your approval. Demo data, fictional customer.</FootNote>
    </>
  );
}
