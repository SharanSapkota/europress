import { Fragment, useEffect, useState } from "react";
import { getCosts, type Container, type Costs } from "../api/costs";
import { useDashboard } from "../components/HeaderTools";
import { Chip, DataTable, FootNote, InfoIcon, PageTitle, TableHeader } from "../components/ui";

const MONTHS = 3;
const whole = new Intl.NumberFormat("fi-FI", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const perT = (cents: number | null) => (cents === null ? null : `${whole.format(cents / 100)}/t`);
const total = (cents: number) => (cents < 0 ? "−" : "") + whole.format(Math.abs(cents) / 100);
const times = (r: number) => `${r.toFixed(1)}×`;

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Costs };

function groups(containers: Container[]) {
  const out = new Map<string, Container[]>();
  for (const c of containers) {
    const key = c.site_label ?? "Other";
    out.set(key, [...(out.get(key) ?? []), c]);
  }
  return [...out.entries()];
}

export function CostsPage() {
  const { load: ctx } = useDashboard();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [site, setSite] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getCosts(MONTHS, site)
      .then((data) => live && setLoad({ state: "ready", data }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [attempt, site]);

  const sites = ctx.state === "ready" ? ctx.data.sites : [];
  const data = load.state === "ready" ? load.data : null;

  return (
    <>
      <PageTitle
        title="Cost per tonne"
        subtitle={data ? `${data.site_count} ${data.site_count === 1 ? "site" : "sites"} · last ${data.months} months` : undefined}
        context=""
        right={
          <label className="month-select">
            <span className="label">Site</span>
            <select value={site} onChange={(e) => setSite(e.target.value)}>
              <option value="">All my sites</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </label>
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

      {data &&
        (data.containers.length === 0 ? (
          <p className="status-text">No pickups in the last {MONTHS} months.</p>
        ) : (
          <>
            {data.highlight && (
              <section className="cost-highlight" aria-label="Most expensive container">
                <span className="cost-highlight-ratio">{times(data.highlight.ratio)}</span>
                <div>
                  <p className="cost-highlight-text">{data.highlight.sentence}</p>
                  {data.highlight.reason && <p className="cost-highlight-reason">{data.highlight.reason}</p>}
                </div>
              </section>
            )}
            <DataTable>
              <table className="costs-table">
                <TableHeader cells={["Container", "Your cost", "Normal", "Compared", <span className="visually-hidden">Details</span>]} />
                <tbody>
                  {groups(data.containers).map(([siteName, list]) => (
                    <Fragment key={siteName}>
                      <tr className="group-row">
                        <th colSpan={5} scope="colgroup">
                          {siteName}
                        </th>
                      </tr>
                      {list.map((c) => (
                        <CostRow
                          key={c.device_id}
                          c={c}
                          open={open === c.device_id}
                          onToggle={() => setOpen(open === c.device_id ? null : c.device_id)}
                        />
                      ))}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </DataTable>
          </>
        ))}
      <FootNote>
        Lighter numbers are based on fewer than 10 weighed pickups. Cost per tonne is left out when the weight is unknown. Demo
        data.
      </FootNote>
    </>
  );
}

function CostRow({ c, open, onToggle }: { c: Container; open: boolean; onToggle: () => void }) {
  const detailsId = `cost-${c.device_id}`;
  const unsure = c.confidence !== "sure";
  const above = c.status === "CHECK";
  const width = c.ratio === null ? 0 : Math.min(1, c.ratio / 3) * 100;
  return (
    <Fragment>
      <tr className={`row${unsure ? " is-unsure" : ""}${open ? " is-open" : ""}`}>
        <th scope="row" className="cell-title">
          {c.name}
        </th>
        <td>
          {c.cost_per_t_cents === null ? (
            <span className="muted">Weight unknown</span>
          ) : (
            <span className="amount amount-line cost-value">
              {perT(c.cost_per_t_cents)}
              <InfoIcon info={c.why.cost_per_t} label={`your cost for ${c.full_name}`} lead={`Based on ${c.pickups} pickups · ${c.confidence}`} />
            </span>
          )}
        </td>
        <td className="cost-normal">{perT(c.benchmark_cents_per_t) ?? "–"}</td>
        <td>
          {c.ratio !== null && (
            <span className="compare">
              <span className="compare-track">
                <span className={above ? "compare-fill is-check" : "compare-fill"} style={{ width: `${width}%` }} />
              </span>
              <Chip tone={above ? "check" : "neutral"}>{above ? `${times(c.ratio)} normal` : "Normal"}</Chip>
            </span>
          )}
        </td>
        <td className="action">
          <button type="button" className="link-small link-chevron" aria-expanded={open} aria-controls={detailsId} onClick={onToggle}>
            {open ? "Hide" : "Details"} <span aria-hidden="true">›</span>
            <span className="visually-hidden"> for {c.full_name}</span>
          </button>
        </td>
      </tr>
      {open && (
        <tr className="details-row" id={detailsId}>
          <td colSpan={5}>
            <div className="details">
              <dl className="breakdown">
                <div>
                  <dt className="label">Pickup fees</dt>
                  <dd>
                    {total(c.breakdown.pickup_fees_cents)}
                    <InfoIcon info={c.why.pickup_fees} label="pickup fees" />
                  </dd>
                </div>
                <div>
                  <dt className="label">Weight fees</dt>
                  <dd>
                    {total(c.breakdown.weight_fees_cents)}
                    <InfoIcon info={c.why.weight_fees} label="weight fees" />
                  </dd>
                </div>
                <div>
                  <dt className="label">Material credit</dt>
                  <dd>
                    {total(c.breakdown.material_credit_cents)}
                    <InfoIcon info={c.why.material_credit} label="material credit" />
                  </dd>
                </div>
              </dl>
              <p className="reason">
                <strong className="strong">Main reason:</strong> {c.main_reason}
                <InfoIcon info={c.why.main_reason} label={`main reason for ${c.full_name}`} />
              </p>
              <p className="note">{c.sources_text}</p>
            </div>
          </td>
        </tr>
      )}
    </Fragment>
  );
}
