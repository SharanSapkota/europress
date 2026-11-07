import { Fragment, useEffect, useState } from "react";
import { getCosts, type Container, type Costs } from "../api/costs";
import { Why } from "../components/Why";

const MONTHS = 3;
const whole = new Intl.NumberFormat("fi-FI", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const perT = (cents: number | null) => (cents === null ? null : `${whole.format(cents / 100)}/t`);
const total = (cents: number) => (cents < 0 ? "−" : "") + whole.format(Math.abs(cents) / 100);

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Costs };

function scope(data: Costs) {
  const sites = data.site_names.length === 1 ? data.site_names[0] : `${data.site_names.length} sites`;
  return `${sites} · last ${data.months} months`;
}

export function CostsPage() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getCosts(MONTHS)
      .then((data) => live && setLoad({ state: "ready", data }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [attempt]);

  return (
    <>
      <h1>Cost per tonne</h1>
      {load.state === "ready" && load.data.containers.length > 0 && <p className="muted subtitle">{scope(load.data)}</p>}

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
        (load.data.containers.length === 0 ? (
          <p className="status-text">No pickups in the last {MONTHS} months.</p>
        ) : (
          <>
            <p className="headline">{load.data.headline}</p>
            <div className="table-box">
              <table className="comparison costs">
                <thead>
                  <tr>
                    <th scope="col">Container</th>
                    <th scope="col">Your cost</th>
                    <th scope="col">Normal</th>
                    <th scope="col">Compared</th>
                    <th scope="col">Based on</th>
                    <th scope="col"><span className="visually-hidden">Details</span></th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.containers.map((c) => (
                    <CostRow
                      key={c.device_id}
                      c={c}
                      open={open === c.device_id}
                      onToggle={() => setOpen(open === c.device_id ? null : c.device_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
            <p className="note">Cost per tonne is left out when the weight is unknown.</p>
          </>
        ))}
    </>
  );
}

function CostRow({ c, open, onToggle }: { c: Container; open: boolean; onToggle: () => void }) {
  const detailsId = `cost-${c.device_id}`;
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <th scope="row" className="container-name">
          {c.name}
          {c.site_name && <span className="sub">{c.site_name}</span>}
        </th>
        <td className="amount big" data-label="Your cost">
          {perT(c.cost_per_t_cents) ?? <span className="muted">Weight unknown</span>}
          <Why info={c.why.cost_per_t} label={`your cost for ${c.full_name}`} />
        </td>
        <td className="muted" data-label="Normal">
          {perT(c.benchmark_cents_per_t) ?? "–"}
          <Why info={c.why.benchmark} label={`normal rate for ${c.full_name}`} />
        </td>
        <td data-label="Compared">
          {c.ratio_label ? (
            <span className={`chip ${c.status === "CHECK" ? "chip-check" : "chip-explained"}`}>{c.ratio_label}</span>
          ) : (
            <span className="muted">–</span>
          )}
          <Why info={c.why.ratio} label={`comparison for ${c.full_name}`} />
        </td>
        <td className="muted" data-label="Based on">
          {c.pickups} pickups · {c.confidence}
          <Why info={c.why.pickups} label={`pickups for ${c.full_name}`} />
        </td>
        <td className="action">
          <button type="button" className="link" aria-expanded={open} aria-controls={detailsId} onClick={onToggle}>
            {open ? "Hide" : "Details"}
            <span className="visually-hidden"> for {c.full_name}</span>
          </button>
        </td>
      </tr>
      {open && (
        <tr className="details-row" id={detailsId}>
          <td colSpan={6}>
            <div className="details">
              <dl className="breakdown">
                <div>
                  <dt className="label">Pickup fees</dt>
                  <dd>
                    {total(c.breakdown.pickup_fees_cents)}
                    <Why info={c.why.pickup_fees} label="pickup fees" />
                  </dd>
                </div>
                <div>
                  <dt className="label">Weight fees</dt>
                  <dd>
                    {total(c.breakdown.weight_fees_cents)}
                    <Why info={c.why.weight_fees} label="weight fees" />
                  </dd>
                </div>
                <div>
                  <dt className="label">Material credit</dt>
                  <dd>
                    {total(c.breakdown.material_credit_cents)}
                    <Why info={c.why.material_credit} label="material credit" />
                  </dd>
                </div>
              </dl>
              <p className="reason">
                <strong className="strong">Main reason:</strong> {c.main_reason}
                <Why info={c.why.main_reason} label={`limits for ${c.full_name}`} />
              </p>
              <p className="note">{c.sources_text}</p>
            </div>
          </td>
        </tr>
      )}
    </Fragment>
  );
}
