import { Fragment, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
  getSecondaryIdeas,
  type BipartiteDeconvRow,
  type Day0AndCreditRow,
  type MinChargeAndMassRow,
  type RightSizerRow,
  type SecondaryIdeas,
} from "../api/weightIdeas";
import { IdeaApprovalBlock } from "../components/IdeaApprovalBlock";
import { Why } from "../components/Why";
import { eur } from "../format";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: SecondaryIdeas };

export function SecondaryIdeasPage() {
  const [params, setParams] = useSearchParams();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);
  const customerId = params.get("customer_id") ?? "all";

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getSecondaryIdeas(customerId)
      .then((data) => live && setLoad({ state: "ready", data }))
      .catch(() => live && setLoad({ state: "failed" }));
    return () => {
      live = false;
    };
  }, [customerId, attempt]);

  const chooseCustomer = (val: string) => {
    const next = new URLSearchParams(params);
    if (val && val !== "all") next.set("customer_id", val);
    else next.delete("customer_id");
    setParams(next);
  };

  return (
    <>
      <div className="title-row">
        <div>
          <h1>Secondary weight ideas (1, 2, 4, 7) &amp; business case</h1>
          <p className="muted subtitle">
            Supporting weight-driven services &amp; Task D commercial model ·{" "}
            <Link to="/primary-ideas">← Back to primary ideas (5, 3, 6)</Link>
          </p>
        </div>
        {load.state === "ready" && (
          <label className="month-select">
            <span className="label">Customer scope</span>
            <select value={customerId} onChange={(e) => chooseCustomer(e.target.value)}>
              <option value="all">All customers</option>
              {load.data.customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      {load.state === "loading" && (
        <p className="status-text" role="status">
          Loading
        </p>
      )}

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
          <dl className="totals">
            <div>
              <dt>
                Idea 1 · Min-charge top-ups &amp; mass trigger
                <Why info={load.data.why.idea1_summary} label="Idea 1 summary" />
              </dt>
              <dd>{eur(load.data.idea1_mass_trigger.reduce((s, r) => s + r.min_charge_topup_cents, 0))}</dd>
              <span className="sub">
                Across {load.data.idea1_mass_trigger.reduce((s, r) => s + r.min_charge_lifts, 0)} light-mass pickups
                (zero bridging dependency)
              </span>
            </div>
            <div>
              <dt>
                Idea 2 · Day-0 weight receipt &amp; credits
                <Why info={load.data.why.idea2_summary} label="Idea 2 summary" />
              </dt>
              <dd>{eur(load.data.idea2_day0_receipt.reduce((s, r) => s + r.unlocked_annual_cents, 0))}/yr</dd>
              <span className="sub">
                Covers missing/&gt;7d tickets &amp; 0 bp recyclable contracts (hypothetical)
              </span>
            </div>
            <div>
              <dt>
                Ideas 4 &amp; 7 · Deconvolution &amp; right-sizer
                <Why info={load.data.why.idea4_summary} label="Idea 4 summary" />
              </dt>
              <dd>
                {load.data.idea4_deconvolution.length} diagnostics · {load.data.idea7_rightsizer.length} upgrades
                <Why info={load.data.why.idea7_summary} label="Idea 7 summary" />
              </dd>
              <span className="sub">Separates truck stored tare from sensor calibration + COMBI → DUO</span>
            </div>
          </dl>

          {/* IDEA 1 */}
          <section className="data-section" style={{ marginTop: "40px" }}>
            <p className="label">Secondary idea 1 of 4 · Idea 1 (Task C)</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              <code>MASS_TARGET_TRIGGER</code> &amp; contractual minimum-tonnage break-even guard (
              <code>MIN_CHARGE_TOPUP</code>)
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              Pressure-based <code>fill_pct</code> (%) cannot tell when a container's physical weight (kg) crosses the
              contract's <code>min_charge_cents</code> break-even tonnage. Dispatches when{" "}
              <code>telemetry_hourly.mass_kg</code> reaches target mass while strictly enforcing the 7-day biowaste
              hygiene rule and <code>max_days_between_collections</code>. Note: ram bridging is resolved by pressing
              multiple times in the field and is never claimed as a problem here.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Compactor &amp; Site</th>
                    <th scope="col">Min-charge top-ups</th>
                    <th scope="col">Median vs. break-even mass</th>
                    <th scope="col">Max interval constraint</th>
                    <th scope="col">Est. annual saving</th>
                    <th scope="col">Status</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea1_mass_trigger.map((r) => (
                    <Idea1Row
                      key={r.item_id}
                      r={r}
                      customerId={customerId}
                      open={openId === r.item_id}
                      onToggle={() => setOpenId(openId === r.item_id ? null : r.item_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* IDEA 2 */}
          <section className="data-section" style={{ marginTop: "56px" }}>
            <p className="label">Secondary idea 2 of 4 · Idea 2 (Tasks A, B, B2, C2)</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Economic Model §2b Day-0 source-weight receipt (±3.3%) &amp; recyclable credit share unlock
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              Provides an immediate Day-0 provisional weight receipt (
              <code>device_estimated_collected_kg ± 3.3%</code>) when scale tickets are unshared or delayed &gt;7 days,
              and flags recyclable contracts (<code>cardboard</code>, <code>plastic_film</code>,{" "}
              <code>mixed_plastic</code> only—never paper, mixed waste, or biowaste) where{" "}
              <code>credit_share_bp = 0</code>.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Contract &amp; Site</th>
                    <th scope="col">Missing / &gt;7d tickets</th>
                    <th scope="col">&gt;10% single-load gaps</th>
                    <th scope="col">Credit share (bp)</th>
                    <th scope="col">Est. annual value</th>
                    <th scope="col">Status</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea2_day0_receipt.map((r) => (
                    <Idea2Row
                      key={r.item_id}
                      r={r}
                      customerId={customerId}
                      open={openId === r.item_id}
                      onToggle={() => setOpenId(openId === r.item_id ? null : r.item_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* IDEA 4 */}
          <section className="data-section" style={{ marginTop: "56px" }}>
            <p className="label">Secondary idea 3 of 4 · Idea 4 (Tasks B, B2, E)</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Bipartite weight deconvolution: hauler truck stored-tare vs. compactor sensor calibration
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              A weight difference between scale ticket and compactor is not automatically the operator's fault. By
              comparing <code>vehicle_id</code> (<code>STORED_VEHICLE_TARE</code> vs. <code>WEIGHED_TARE</code>) across
              sites against <code>maintenance_work_orders</code> (<code>WEIGHT_RECALIBRATION</code>,{" "}
              <code>WEIGHT_SENSOR_REPLACED</code>), we separate outdated truck stored tares from compactor sensor
              calibration windows.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Attributed source</th>
                    <th scope="col">Vehicle or Device</th>
                    <th scope="col">Stored vs. weighed tare</th>
                    <th scope="col">Avg. weight gap</th>
                    <th scope="col">Financial / service impact</th>
                    <th scope="col">Recommended action</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea4_deconvolution.map((r) => (
                    <Idea4Row
                      key={r.item_id}
                      r={r}
                      customerId={customerId}
                      open={openId === r.item_id}
                      onToggle={() => setOpenId(openId === r.item_id ? null : r.item_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* IDEA 7 */}
          <section className="data-section" style={{ marginTop: "56px" }}>
            <p className="label">Secondary idea 4 of 4 · Idea 7 (Task D Hardware Pull-Through)</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Tonnage-verified compaction force tuning &amp; <code>COMBI</code> → <code>DUO</code> lease right-sizer
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              Verifies payload density (kg/m³) from <code>device_estimated_collected_kg</code> after{" "}
              <code>COMPACTION_FORCE_SETTING_INCREASED</code> work orders and identifies non-biowaste{" "}
              <code>COMBI</code> (≤22 m³) containers with frequent lifts where upgrading to a 24–30 m³ Europress{" "}
              <code>DUO</code> lowers customer lift costs while increasing Europress lease revenue.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Device &amp; Site</th>
                    <th scope="col">Equipment &amp; density</th>
                    <th scope="col">Recommended upgrade / tuning</th>
                    <th scope="col">Customer saving (est.)</th>
                    <th scope="col">Europress lease/service</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea7_rightsizer.map((r) => (
                    <Idea7Row
                      key={r.item_id}
                      r={r}
                      customerId={customerId}
                      open={openId === r.item_id}
                      onToggle={() => setOpenId(openId === r.item_id ? null : r.item_id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* TASK D BUSINESS CASE & SENSITIVITY */}
          <section className="data-section" style={{ marginTop: "56px" }}>
            <p className="label">Task D Deliverable · Commercial packaging &amp; sensitivity</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Task D business case: pricing, cost to serve, payback &amp; 5-scenario sensitivity
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              Explicit commercial assumptions (<code>configs/my_params.yaml</code>): cost to serve{" "}
              <strong>{eur(load.data.business_case.cost_to_serve_cents_month)}/device/month</strong>
              <Why info={load.data.business_case.why.cost_to_serve} label="cost to serve" />, base customer payback{" "}
              <strong>{load.data.business_case.payback_months} months</strong>
              <Why info={load.data.business_case.why.payback} label="customer payback" /> across{" "}
              {load.data.business_case.fleet_weighed_devices} weighed compactors (of{" "}
              {load.data.business_case.fleet_devices_total} total in the full synthetic benchmark). Europress is not
              currently a party to customer–operator waste contracts; all figures below are hypothetical estimates.
            </p>

            <div className="cards" style={{ marginTop: "24px" }}>
              {load.data.business_case.tiers.map((t) => (
                <article key={t.tier_id} className="card">
                  <div className="card-head">
                    <h2>{t.name}</h2>
                    <span className="amount big">
                      €{t.price_eur_month}/mo
                      <Why info={t.why} label={t.name} />
                    </span>
                  </div>
                  <p className="muted card-scope">{t.target_segment}</p>
                  <p style={{ margin: "0 0 12px" }}>{t.included_ideas}</p>
                  <p className="note">
                    <strong className="strong">Customer ROI:</strong> {t.customer_net_roi}
                  </p>
                </article>
              ))}
            </div>

            <h3 style={{ margin: "32px 0 12px", color: "var(--primary)" }}>
              Sensitivity analysis (adoption, value realisation &amp; degraded sensor noise)
            </h3>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Scenario</th>
                    <th scope="col">Adoption</th>
                    <th scope="col">Value realisation</th>
                    <th scope="col">Sensor noise</th>
                    <th scope="col">Customer net benefit/yr</th>
                    <th scope="col">Europress ARR</th>
                    <th scope="col">Europress net margin</th>
                    <th scope="col">Payback</th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.business_case.sensitivity.map((s) => (
                    <tr key={s.scenario} className="row">
                      <td>
                        <span className="strong">{s.scenario}</span>
                        <Why info={s.why} label={s.scenario} />
                      </td>
                      <td>{s.adoption_pct.toFixed(0)}%</td>
                      <td>{s.realisation_pct.toFixed(1)}%</td>
                      <td>±{s.sensor_noise_pct.toFixed(1)}%</td>
                      <td className="amount">{eur(s.customer_net_benefit_cents)}</td>
                      <td className="amount">{eur(s.europress_arr_cents)}</td>
                      <td className="amount">{eur(s.europress_net_margin_cents)}</td>
                      <td>{s.payback_months.toFixed(1)} mo</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}

function Idea1Row({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: MinChargeAndMassRow;
  customerId: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <td>
          <span className="strong">{r.device_id}</span> · {r.site_name}
          <span className="sub">
            {r.material} · Policy: {r.collection_policy}
          </span>
        </td>
        <td className="amount">
          {eur(r.min_charge_topup_cents)}
          <Why info={r.why.min_charge} label={`min charge for ${r.device_id}`} />
          <span className="sub">{r.min_charge_lifts} pickups with top-up</span>
        </td>
        <td>
          Median {r.median_mass_before_kg} kg vs. <strong>{r.break_even_mass_kg} kg</strong>
          <Why info={r.why.mass_trigger} label={`mass trigger for ${r.device_id}`} />
        </td>
        <td className="muted">Max {r.max_days ?? 14} days</td>
        <td className="amount">
          {eur(r.annual_saving_cents)}/yr
          <span className="sub">Hypothetical estimate</span>
        </td>
        <td>
          <span className={`chip ${r.status === "CHECK" ? "chip-check" : "chip-explained"}`}>
            {r.status === "CHECK" ? "Mass trigger" : "Normal"}
          </span>
        </td>
        <td className="action">
          <button type="button" className="link" aria-expanded={open} onClick={onToggle}>
            {open ? "Hide" : "Proposal"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="details-row">
          <td colSpan={7}>
            <IdeaApprovalBlock
              itemId={r.item_id}
              customerId={customerId}
              suggestion={r.suggestion}
              reason={r.reason}
              trailText={r.trail_text}
              initialDecision={r.decision}
              initialDraft={r.draft}
            />
          </td>
        </tr>
      )}
    </Fragment>
  );
}

function Idea2Row({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: Day0AndCreditRow;
  customerId: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <td>
          <span className="strong">{r.contract_id}</span> · {r.site_name}
          <span className="sub">
            {r.operator_id} · {r.device_id} · {r.material}
          </span>
        </td>
        <td>
          {r.unshared_or_delayed_lifts} pickups ({r.provisional_receipt_kg.toLocaleString("fi-FI")} kg)
          <Why info={r.why.day0_receipt} label={`day 0 receipt for ${r.contract_id}`} />
        </td>
        <td>{r.weight_gap_lifts} single-load pickups</td>
        <td>
          {r.credit_eligible ? (
            <span className={`chip ${r.credit_share_bp === 0 ? "chip-check" : "chip-explained"}`}>
              {r.credit_share_bp} bp ({r.credit_share_bp / 100}%)
            </span>
          ) : (
            <span className="muted">Not credit-eligible</span>
          )}
        </td>
        <td className="amount">
          {eur(r.unlocked_annual_cents)}/yr
          <Why info={r.why.credit_unlock} label={`credit unlock for ${r.contract_id}`} />
        </td>
        <td>
          <span className={`chip ${r.status === "CHECK" ? "chip-check" : "chip-explained"}`}>
            {r.status === "CHECK" ? "Review clause" : "Normal"}
          </span>
        </td>
        <td className="action">
          <button type="button" className="link" aria-expanded={open} onClick={onToggle}>
            {open ? "Hide" : "Proposal"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="details-row">
          <td colSpan={7}>
            <IdeaApprovalBlock
              itemId={r.item_id}
              customerId={customerId}
              suggestion={r.suggestion}
              reason={r.reason}
              trailText={r.trail_text}
              initialDecision={r.decision}
              initialDraft={r.draft}
            />
          </td>
        </tr>
      )}
    </Fragment>
  );
}

function Idea4Row({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: BipartiteDeconvRow;
  customerId: string;
  open: boolean;
  onToggle: () => void;
}) {
  const isTruck = r.source_side === "HAULER_STORED_TARE";
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <td>
          <span className={`chip ${isTruck ? "chip-check" : "chip-explained"}`}>{r.source_label}</span>
        </td>
        <td>
          <span className="strong">{r.entity_id}</span>
          <span className="sub">
            {r.operator_or_site} · {r.lifts_or_orders} {isTruck ? "stored-tare pickups" : "work order(s)"}
          </span>
        </td>
        <td>
          {isTruck ? (
            <>
              Stored: {r.stored_tare_kg} kg
              <span className="sub">
                Weighed: {r.weighed_tare_kg ? `${r.weighed_tare_kg} kg` : "None on file"}
              </span>
            </>
          ) : (
            <span className="muted">Compactor load cell</span>
          )}
        </td>
        <td className="amount">
          {isTruck ? `${r.avg_weight_gap_kg > 0 ? "+" : ""}${r.avg_weight_gap_kg} kg` : "Calibration window"}
          <Why info={r.why.gap} label={`gap for ${r.entity_id}`} />
        </td>
        <td className="amount">
          {eur(r.financial_impact_cents)}
          <Why info={r.why.impact} label={`impact for ${r.entity_id}`} />
        </td>
        <td className="muted">{r.europress_action}</td>
        <td className="action">
          <button type="button" className="link" aria-expanded={open} onClick={onToggle}>
            {open ? "Hide" : "Proposal"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="details-row">
          <td colSpan={7}>
            <IdeaApprovalBlock
              itemId={r.item_id}
              customerId={customerId}
              suggestion={r.suggestion}
              reason={r.reason}
              trailText={r.trail_text}
              initialDecision={r.decision}
              initialDraft={r.draft}
            />
          </td>
        </tr>
      )}
    </Fragment>
  );
}

function Idea7Row({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: RightSizerRow;
  customerId: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <td>
          <span className="strong">{r.device_id}</span> · {r.site_name}
          <span className="sub">
            {r.material} · {r.lifts_count} weighed pickups
          </span>
        </td>
        <td className="amount">
          {r.measured_density_kg_m3.toFixed(1)} kg/m³
          <Why info={r.why.density} label={`density for ${r.device_id}`} />
          <span className="sub">
            {r.equipment_class} {r.volume_m3} m³
          </span>
        </td>
        <td>{r.upgrade_path}</td>
        <td className="amount">
          {eur(r.customer_annual_saving_cents)}/yr
          <Why info={r.why.customer_saving} label={`customer saving for ${r.device_id}`} />
        </td>
        <td className="amount">
          +{eur(r.europress_annual_revenue_cents)}/yr
          <Why info={r.why.europress_revenue} label={`europress revenue for ${r.device_id}`} />
        </td>
        <td className="action">
          <button type="button" className="link" aria-expanded={open} onClick={onToggle}>
            {open ? "Hide" : "Proposal"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="details-row">
          <td colSpan={6}>
            <IdeaApprovalBlock
              itemId={r.item_id}
              customerId={customerId}
              suggestion={r.suggestion}
              reason={r.reason}
              trailText={r.trail_text}
              initialDecision={r.decision}
              initialDraft={r.draft}
            />
          </td>
        </tr>
      )}
    </Fragment>
  );
}
