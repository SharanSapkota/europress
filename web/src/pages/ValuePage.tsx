import { useEffect, useState } from "react";
import { getValue, type ValuePage as Value } from "../api/value";
import { FootNote, PageTitle, TotalsPanel } from "../components/ui";
import { eurWhole, signedWhole } from "../format";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: Value };

const euros = new Intl.NumberFormat("fi-FI", { maximumFractionDigits: 0 });

export function ValuePage() {
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getValue()
      .then((data) => live && setLoad({ state: "ready", data }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [attempt]);

  const months = load.state === "ready" ? load.data.months : 3;

  return (
    <>
      <PageTitle
        title="Your value"
        subtitle={`What Smart Weight found for you in the last ${months} months, and what it costs.`}
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
      {load.state === "ready" && (
        <>
          <TotalsPanel
            items={[
              { label: "Value found", value: eurWhole(load.data.value_found_cents), info: load.data.why.found, tag: "Estimate" },
              { label: "Plan cost", value: eurWhole(load.data.plan_cost_cents), info: load.data.why.cost, tag: "Example price" },
              { label: "Net for you", value: signedWhole(load.data.net_cents), tag: "Estimate" },
            ]}
          />
          <div className="plan-grid">
            {load.data.plans.map((p) => (
              <section key={p.key} className={p.current ? "card plan-card is-current" : "card plan-card"} aria-label={`${p.name} plan`}>
                {p.current && <span className="plan-badge">Your plan</span>}
                <h2 className="plan-name">{p.name}</h2>
                <p className="plan-price">
                  {p.price_eur === null ? (
                    "Included"
                  ) : (
                    <>
                      {euros.format(p.price_eur)} € <span className="plan-unit">/ container / month</span>
                    </>
                  )}
                </p>
                <ul className="plan-list">
                  {p.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
                {p.key === "pro" && (
                  <button type="button" className="btn btn-outline plan-compare">
                    Compare
                  </button>
                )}
              </section>
            ))}
          </div>
          <section className="europress-bar" aria-label="Europress view">
            <div>
              <p className="europress-label">Europress view</p>
              <p className="europress-text">{load.data.europress.text}</p>
            </div>
            <p className="europress-value">{euros.format(load.data.europress.yearly_eur)} € / year</p>
          </section>
        </>
      )}
      <FootNote>Plan prices and adoption are example assumptions, not offers. Value found is estimated from demo data.</FootNote>
    </>
  );
}
