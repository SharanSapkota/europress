import { Link } from "react-router";

type Rule = { rule: string; status: string; where: string; to?: string };

const FACTS: Rule[] = [
  {
    rule: "Europress is not a party to waste transport or treatment and does not know the real prices.",
    status: "Confirmed by Europress",
    where: "Invoices labels our total \"Our invoice (estimate)\", every footer says our amounts are estimates, and every Why? on our amounts names your contract version as the price source.",
    to: "/",
  },
  {
    rule: "Only cardboard and plastics earn a material credit. Paper and other streams are charged.",
    status: "Confirmed by Europress",
    where: "Our invoice gives a material credit only for credit-eligible materials. Primary ideas (Idea 5) and Secondary ideas (Idea 2) apply credit logic strictly to cardboard, plastic film and mixed plastic.",
    to: "/primary-ideas",
  },
  {
    rule: "Material quality is set only by the operator at its facility.",
    status: "Confirmed by Europress",
    where: "Invoices, Details, \"Where the numbers come from\": the quality grade names the operator's quality assessment. When none is shared, it says \"Not shared (grade A assumed)\" and the pickup gets Not enough data with that reason.",
    to: "/",
  },
  {
    rule: "Europress does not know which facility the operator uses.",
    status: "Confirmed by Europress",
    where: "No screen uses or shows the facility.",
  },
  {
    rule: "Most devices are emptied on call; a few run on a fixed schedule.",
    status: "Direction confirmed; the exact mix is synthetic",
    where: "Cost per tonne mentions a fixed schedule only for fixed-schedule devices. Low-fill pickups required by the maximum interval, the hygiene limit or a pre-closure order are not counted as a cause.",
    to: "/costs",
  },
  {
    rule: "Equipment classes COMBI and DUO.",
    status: "Europress machine types",
    where: "Primary ideas (Idea 3) checks COMBI (≤22 m³, all biowaste) for winter frozen biowaste and heated floor options; Secondary ideas (Idea 7) checks non-biowaste COMBI units for 24–30 m³ DUO lease upgrades.",
    to: "/secondary-ideas",
  },
  {
    rule: "Integrated weighing gives usable weights (a future scenario; most devices have it).",
    status: "Challenge assumption, not proven",
    where: "The scale ticket comes first, then invoice tonnage, then the device weight. A weight is never guessed. The device weight is tagged Estimated.",
    to: "/",
  },
  {
    rule: "Device weighing accuracy is about ±3.3 %; fault states exceed it.",
    status: "Simulation target set with Europress",
    where: "Device weights show ± 3.3 %. Secondary ideas (Idea 2 & Task D sensitivity) model both ±3.3 % normal tolerance and ±6.5 % degraded sensor noise.",
    to: "/secondary-ideas",
  },
  {
    rule: "Fill estimate accuracy is about ±4 percentage points.",
    status: "Accepted synthetic assumption",
    where: "Fill is used as the median fill before pickup in Cost per tonne and combined with mass_kg to compute measured bulk density (kg/m³) in Idea 5 and Idea 7.",
    to: "/primary-ideas",
  },
  {
    rule: "Operators differ in data sharing (0–97 %), sharing delay and invoice accuracy.",
    status: "Synthetic assumption; operators are fictional",
    where: "Operators shows tickets shared, the delay, and invoice lines to check per operator, each with Good or Check. Idea 2 provides a Day-0 provisional weight receipt for missing or >7d delayed tickets.",
    to: "/operators",
  },
  {
    rule: "Tariffs, gate fees, credit shares, surcharges and minimum charges are hypothetical.",
    status: "Hypothetical",
    where: "Used only as your contract terms. The Why? on our amounts and on each invoice line names the contract version.",
    to: "/",
  },
  {
    rule: "Material price indices are synthetic.",
    status: "Synthetic illustrative index",
    where: "Used only for the material credit. Cost per tonne, Details: the Why? on material credit says it comes from the price index and the quality grade.",
    to: "/costs",
  },
  {
    rule: "Business-case prices, cost to serve and adoption are not given.",
    status: "Teams choose and justify them",
    where: "Secondary ideas & Task D presents our 3-tier pricing (€29 / €49 / €110 per month), €8.50/month cost to serve, 1.6-month payback, and 5-scenario sensitivity table.",
    to: "/secondary-ideas",
  },
  {
    rule: "Valuation rules for disputes, renegotiation and tenders are hypothetical.",
    status: "Hypothetical, published",
    where: "Expected values on Operators and Weight ideas are tagged Hypothetical and say they are not proof of a saving.",
    to: "/operators",
  },
  {
    rule: "Customers, sites, devices, contracts and invoices are fictional.",
    status: "Entirely fictional",
    where: "Every page says Demo data. Operator names carry (fictional). Decisions use a demo user, so no personal data.",
  },
  {
    rule: "No external dataset was imported; no personal data exists.",
    status: "Dataset rule",
    where: "The portal reads only the dataset's own tables and adds no outside data. The only person stored is the demo user on decisions.",
  },
];

const LIMITS: Rule[] = [
  {
    rule: "Not calibrated: euro and €/t levels are not market facts.",
    status: "Limitation",
    where: "Amounts are estimates on demo data; no page claims a real saving.",
  },
  {
    rule: "Simplified logistics: one billable distance per site, combined loads only for the same customer and material.",
    status: "Limitation",
    where: "Combined loads are shown as Explained on Invoices, and Primary ideas (Idea 6) reallocates truck net_kg proportionally across sites using pairwise device_estimated_collected_kg.",
    to: "/primary-ideas",
  },
  {
    rule: "Contamination is one share per load; the grade is a noisy operator assessment.",
    status: "Limitation",
    where: "Invoices, Details: the grade source is the operator's quality assessment. Each flagged item names a likely source (invoice vs contract, measurement, missing data, normal), never blame.",
    to: "/",
  },
  {
    rule: "One device per stream per site; no relocations between sites.",
    status: "Limitation",
    where: "Cost per tonne has one row per container (device), named by material and site.",
    to: "/costs",
  },
  {
    rule: "Operator and contract actions use simple published rules.",
    status: "Limitation",
    where: "Operators and Weight ideas give proposals with reasons; you decide, and you can undo any decision in Decisions.",
    to: "/decisions",
  },
  {
    rule: "Scorecard: punctuality and missed visits are your own records; billing and weights need reconciliation.",
    status: "Limitation",
    where: "On time and missed visits are tagged Observed; invoice lines and weight vs ours are Estimated. Secondary ideas (Idea 4) deconvolves vehicle stored-tare gaps from compactor sensor calibration.",
    to: "/secondary-ideas",
  },
  {
    rule: "Service-quality effects of switching operator are not modelled.",
    status: "Limitation",
    where: "A tender is suggested only after a declined renegotiation, and its value compares only price and billing accuracy.",
    to: "/operators",
  },
  {
    rule: "press_load_index is derived from the device's own (biased) fill estimate.",
    status: "Limitation",
    where: "Not used.",
  },
  {
    rule: "Ram/cardboard bridging (S40) is resolved in the field by pressing multiple times.",
    status: "Confirmed by Europress judge",
    where: "We never claim bridging detection as a value driver. Secondary ideas (Idea 1) uses mass_kg strictly for contractual min_charge_cents break-even and MASS_TARGET_TRIGGER payload targets.",
    to: "/secondary-ideas",
  },
  {
    rule: "Counterfactual savings (Task C) are simulated, not causal evidence.",
    status: "Limitation",
    where: "Secondary ideas (Idea 1) tags MASS_TARGET_TRIGGER savings as Hypothetical and enforces 7-day hygiene and max_days_between_collections.",
    to: "/secondary-ideas",
  },
  {
    rule: "Maintenance is context only.",
    status: "Limitation",
    where: "Primary ideas (Idea 3) and Secondary ideas (Ideas 4 & 7) cross-check maintenance_work_orders (WEIGHT_RECALIBRATION, WEIGHT_SENSOR_REPLACED, COMPACTION_FORCE_SETTING_INCREASED) to avoid false operator disputes.",
    to: "/primary-ideas",
  },
  {
    rule: "Timestamps are UTC; local logic uses Europe/Helsinki, including summer time.",
    status: "Rule",
    where: "Service dates, months and contract versions use Helsinki local dates. Telemetry is read from the daily summary only (hours full, valid readings).",
  },
  {
    rule: "Enterprise profile (a second-year price shift) is a stress test, not distributed.",
    status: "Limitation",
    where: "Not used; the portal runs on the quickstart pack.",
  },
  {
    rule: "The dataset is synthetic: no figure is Europress customer data, a verified result or a proven saving.",
    status: "Release status",
    where: "Every footer says Demo data. No page claims a real saving, and expected values are tagged Hypothetical.",
  },
  {
    rule: "Every recommendation is a proposal that needs human approval.",
    status: "Rule",
    where: "Nothing is sent to the operator. Every action needs your click, is stored with user and time, and can be undone.",
    to: "/decisions",
  },
];

function Section({ title, rules }: { title: string; rules: Rule[] }) {
  return (
    <section className="data-section">
      <h2 className="label">{title}</h2>
      <div className="table-box">
        <table className="history data-rules">
          <thead>
            <tr>
              <th scope="col">Rule in the dataset</th>
              <th scope="col">Status</th>
              <th scope="col">Where in the portal</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.rule}>
                <td>{r.rule}</td>
                <td className="muted">{r.status}</td>
                <td>
                  {r.where}
                  {r.to && (
                    <>
                      {" "}
                      <Link to={r.to}>Open</Link>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function DataPage() {
  return (
    <>
      <h1>About the data</h1>
      <p className="muted subtitle">How this portal follows the dataset's assumptions and limitations</p>
      <Section title="Facts and assumptions" rules={FACTS} />
      <Section title="Limitations" rules={LIMITS} />
    </>
  );
}
