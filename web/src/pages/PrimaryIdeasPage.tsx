import { Fragment, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
  getPrimaryIdeas,
  type CombinedLoadPair,
  type PrimaryIdeas,
  type ResidualPickupRow,
  type SortingCandidate,
} from "../api/weightIdeas";
import { IdeaApprovalBlock } from "../components/IdeaApprovalBlock";
import { Why } from "../components/Why";
import { eur } from "../format";

type Load = { state: "loading" } | { state: "failed" } | { state: "ready"; data: PrimaryIdeas };

export function PrimaryIdeasPage() {
  const [params, setParams] = useSearchParams();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [attempt, setAttempt] = useState(0);
  const [openId, setOpenId] = useState<string | null>(null);
  const customerId = params.get("customer_id") ?? "all";

  useEffect(() => {
    let live = true;
    setLoad({ state: "loading" });
    getPrimaryIdeas(customerId)
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
          <h1>Primary weight ideas (5, 3, 6)</h1>
          <p className="muted subtitle">
            Core capabilities unlocked exclusively by compactor weight telemetry ·{" "}
            <Link to="/secondary-ideas">View secondary ideas (1, 2, 4, 7) &amp; Task D business case →</Link>
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
                Idea 5 · Mixed-waste sorting value
                <Why info={load.data.why.idea5_summary} label="Idea 5 sorting summary" />
              </dt>
              <dd>{eur(load.data.idea5_sorting.reduce((s, r) => s + r.annual_saving_cents, 0))}/yr</dd>
              <span className="sub">
                {load.data.idea5_sorting.filter((r) => r.status === "CHECK").length} low-density mixed-waste compactors
                (hypothetical)
              </span>
            </div>
            <div>
              <dt>
                Idea 3 · Post-lift residual detections
                <Why info={load.data.why.idea3_summary} label="Idea 3 residual mass summary" />
              </dt>
              <dd>{load.data.idea3_residual.length} pickups</dd>
              <span className="sub">
                Separates physical stuck/frozen waste from sensor zero-offsets (estimated)
              </span>
            </div>
            <div>
              <dt>
                Idea 6 · Combined-load reallocation
                <Why info={load.data.why.idea6_summary} label="Idea 6 combined load summary" />
              </dt>
              <dd>
                {load.data.idea6_combined.reduce((s, r) => s + r.shift_kg, 0).toLocaleString("fi-FI")} kg shifted
              </dd>
              <span className="sub">
                Across {load.data.idea6_combined.length} shared-truck trips (50/50 split vs. device weight)
              </span>
            </div>
          </dl>

          {/* IDEA 5 */}
          <section className="data-section" style={{ marginTop: "40px" }}>
            <p className="label">Primary idea 1 of 3 · Idea 5</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Multi-stream weight-per-m³ sorting diverter &amp; Balex / DUO upsell
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              Divides <code>device_estimated_collected_kg</code> by occupied volume (
              <code>container_volume_m3 × device_fill_pct_before</code>) on mixed-waste compactors. Fill % alone cannot
              distinguish heavy mixed waste (nominal 380 kg/m³) from lightweight mis-sorted cardboard and plastics
              (~205 kg/m³). Only cardboard, plastic film, and mixed plastic earn material credits.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Compactor &amp; Site</th>
                    <th scope="col">Measured density</th>
                    <th scope="col">Est. recyclable in mixed</th>
                    <th scope="col">Annual sorting value</th>
                    <th scope="col">Europress hardware fit</th>
                    <th scope="col">Status</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea5_sorting.map((r) => (
                    <SortingRow
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

          {/* IDEA 3 */}
          <section className="data-section" style={{ marginTop: "56px" }}>
            <p className="label">Primary idea 2 of 3 · Idea 3</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Post-lift residual mass (<code>device_mass_kg_after</code>) for partial emptying &amp; frozen biowaste
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              After a pickup, hydraulic ram pressure drops so <code>device_fill_pct_after</code> reads near 0%, hiding
              waste frozen or stuck inside. <code>device_mass_kg_after</code> measures the exact mass left behind—and
              cross-checks <code>maintenance_work_orders</code> (<code>WEIGHT_RECALIBRATION</code>) so sensor
              zero-offsets are never blamed on the operator.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Pickup &amp; Device</th>
                    <th scope="col">Fill after lift</th>
                    <th scope="col">Mass after lift</th>
                    <th scope="col">Diagnosis</th>
                    <th scope="col">Wasted lift capacity</th>
                    <th scope="col">Europress action</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea3_residual.map((r) => (
                    <ResidualRow
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

          {/* IDEA 6 */}
          <section className="data-section" style={{ marginTop: "56px" }}>
            <p className="label">Primary idea 3 of 3 · Idea 6</p>
            <h2 style={{ margin: "0 0 8px", color: "var(--primary)" }}>
              Combined-load (50/50 split) proportional source-weight re-allocator
            </h2>
            <p className="muted" style={{ marginTop: 0, maxWidth: "880px" }}>
              When a collection truck empties two compactors on one trip (<code>loads_on_vehicle = 2</code>,{" "}
              <code>EQUAL_SPLIT_COMBINED_LOAD</code>), the scale ticket splits total <code>net_kg</code> 50/50. Using
              pairwise <code>device_estimated_collected_kg</code> (<code>m_A</code> and <code>m_B</code>), we reallocate
              the certified scale weight proportionally: <code>net_kg × m_A / (m_A + m_B)</code>.
            </p>
            <div className="table-box">
              <table className="comparison">
                <thead>
                  <tr>
                    <th scope="col">Shared weighing event</th>
                    <th scope="col">Truck scale net</th>
                    <th scope="col">Stop A (device / 50-50 → prop.)</th>
                    <th scope="col">Stop B (device / 50-50 → prop.)</th>
                    <th scope="col">Weight &amp; cost shift</th>
                    <th scope="col">Status</th>
                    <th scope="col">
                      <span className="visually-hidden">Details</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {load.data.idea6_combined.map((r) => (
                    <CombinedRow
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
        </>
      )}
    </>
  );
}

function SortingRow({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: SortingCandidate;
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
            {r.equipment_class} {r.volume_m3} m³ · {r.lifts_count} pickups ({r.total_mass_kg.toLocaleString("fi-FI")} kg)
          </span>
        </td>
        <td className="amount">
          {r.measured_density_kg_m3.toFixed(1)} kg/m³
          <Why info={r.why.density} label={`density for ${r.device_id}`} />
          <span className="sub">Nominal: {r.nominal_density_kg_m3} kg/m³</span>
        </td>
        <td>
          ~{r.estimated_recyclable_kg.toLocaleString("fi-FI")} kg
          <Why info={r.why.recyclable_kg} label={`recyclable mass for ${r.device_id}`} />
        </td>
        <td className="amount">
          {eur(r.annual_saving_cents)}/yr
          <Why info={r.why.annual_saving} label={`annual saving for ${r.device_id}`} />
          <span className="sub">Hypothetical estimate</span>
        </td>
        <td className="muted">{r.europress_hardware}</td>
        <td>
          <span className={`chip ${r.status === "CHECK" ? "chip-check" : "chip-explained"}`}>
            {r.status === "CHECK" ? "Check sorting" : "Normal"}
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

function ResidualRow({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: ResidualPickupRow;
  customerId: string;
  open: boolean;
  onToggle: () => void;
}) {
  const isOffset = r.classification === "CALIBRATION_OFFSET";
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <td>
          <span className="strong">{r.pickup_id}</span> · {r.device_id}
          <span className="sub">
            {r.date} · {r.site_name} · {r.material} ({r.equipment_class}, {r.pickup_status})
          </span>
        </td>
        <td>
          {r.fill_after_pct.toFixed(1)}%
          <Why info={r.why.fill_vs_mass} label={`fill vs mass for ${r.pickup_id}`} />
          <span className="sub">Ram retracted</span>
        </td>
        <td className="amount">
          {r.mass_after_kg} kg ({r.residual_pct.toFixed(1)}%)
          <Why info={r.why.mass_after} label={`mass after for ${r.pickup_id}`} />
          <span className="sub">Before lift: {r.mass_before_kg} kg</span>
        </td>
        <td>
          <span className={`chip ${isOffset ? "chip-explained" : "chip-check"}`}>{r.classification_label}</span>
        </td>
        <td className="amount">
          {isOffset ? "0,00 € (sensor offset)" : eur(r.wasted_capacity_cents)}
          <Why info={r.why.wasted_capacity} label={`wasted capacity for ${r.pickup_id}`} />
        </td>
        <td className="muted">{r.europress_service}</td>
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

function CombinedRow({
  r,
  customerId,
  open,
  onToggle,
}: {
  r: CombinedLoadPair;
  customerId: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <Fragment>
      <tr className={open ? "row is-open" : "row"}>
        <td>
          <span className="strong">{r.weighing_event_id}</span>
          <span className="sub">
            {r.date} · {r.operator_id} · {r.material}
          </span>
        </td>
        <td className="amount">
          {r.truck_net_kg.toLocaleString("fi-FI")} kg
          <Why info={r.why.truck_net} label={`truck net weight for ${r.weighing_event_id}`} />
        </td>
        <td>
          <span className="strong">{r.site_a_name}</span> ({r.device_a_id})
          <span className="sub">
            Device: {r.device_a_kg} kg · 50/50: {r.naive_a_kg} kg → <strong>{r.proportional_a_kg} kg</strong>
          </span>
        </td>
        <td>
          <span className="strong">{r.site_b_name}</span> ({r.device_b_id})
          <span className="sub">
            Device: {r.device_b_kg} kg · 50/50: {r.naive_b_kg} kg → <strong>{r.proportional_b_kg} kg</strong>
          </span>
        </td>
        <td className="amount">
          ±{r.shift_kg} kg ({r.shift_pct.toFixed(0)}%)
          <Why info={r.why.proportional} label={`proportional split for ${r.weighing_event_id}`} />
          <span className="sub">
            {eur(r.reallocated_value_cents)} site shift
            <Why info={r.why.reallocated_value} label={`site reallocation value for ${r.weighing_event_id}`} />
          </span>
        </td>
        <td>
          <span className={`chip ${r.status === "CHECK" ? "chip-check" : "chip-explained"}`}>
            {r.status === "CHECK" ? "Reallocate" : "Close to 50/50"}
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
