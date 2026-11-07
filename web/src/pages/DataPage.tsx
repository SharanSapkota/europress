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
    where: "Our invoice gives a material credit only for credit-eligible materials. Cost per tonne shows the credit separately.",
    to: "/costs",
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
    where: "Not used yet. No calculation depends on the equipment class.",
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
    where: "Device weights show ± 3.3 %. The Why? on the main reason in Cost per tonne gives the share of valid device readings.",
    to: "/costs",
  },
  {
    rule: "Fill estimate accuracy is about ±4 percentage points.",
    status: "Accepted synthetic assumption",
    where: "Fill is used only as the median fill before pickup in Cost per tonne. The ±4 points are not shown yet.",
    to: "/costs",
  },
  {
    rule: "Operators differ in data sharing (0–97 %), sharing delay and invoice accuracy.",
    status: "Synthetic assumption; operators are fictional",
    where: "Operators shows tickets shared, the delay, and invoice lines to check per operator, each with Good or Check.",
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
    where: "Not built yet (Task D).",
  },
  {
    rule: "Valuation rules for disputes, renegotiation and tenders are hypothetical.",
    status: "Hypothetical, published",
    where: "Expected values on Operators are tagged Hypothetical and say they are not proof of a saving.",
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
    where: "Transport uses the contract distance. Combined loads are shown as Explained, not as a difference.",
    to: "/",
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
    where: "Operators gives one suggestion with its reason; you decide, and you can undo it in Decisions.",
    to: "/decisions",
  },
  {
    rule: "Scorecard: punctuality and missed visits are your own records; billing and weights need reconciliation.",
    status: "Limitation",
    where: "On time and missed visits are tagged Observed; invoice lines and weight vs ours are Estimated. Weight vs ours says a gap can come from the device, the weighbridge or a shared truck.",
    to: "/operators",
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
    rule: "Fill sensors can read falsely high for a few days; the mass reading shows it.",
    status: "Limitation",
    where: "Not checked yet. This belongs to the lift checks (premature lifts), which are not built.",
  },
  {
    rule: "Counterfactual savings (Task C) are simulated, not causal evidence.",
    status: "Limitation",
    where: "Not built yet (Task C).",
  },
  {
    rule: "Maintenance is context only.",
    status: "Limitation",
    where: "Not used.",
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
