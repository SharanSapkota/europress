import type { LinePart } from "../api/invoices";
import { eur, material, qty } from "../format";
import type { TableRow } from "./ComparisonTable";

const UNIT: Record<string, string> = { t: "t", km: "km", lift: "lift", event: "event", pct_of_base: "%" };

function partText(p: LinePart | null) {
  if (!p) return { amount: "Not on this invoice", detail: "" };
  if (p.unit === "pct_of_base") return { amount: eur(p.amount_cents), detail: `${qty(p.quantity)} % of ${eur(p.rate_cents ?? 0)}` };
  const unit = UNIT[p.unit ?? ""] ?? p.unit ?? "";
  const rate = p.rate_cents === null ? "" : ` × ${eur(p.rate_cents)}`;
  return { amount: eur(p.amount_cents), detail: `${qty(p.quantity)} ${unit}${rate}` };
}

function trailText(row: TableRow) {
  const t = row.trail;
  const lines = t.invoice_line_ids.length ? `invoice items ${t.invoice_line_ids.join(", ")}` : "not on an invoice";
  return [
    t.pickup_id && `pickup ${t.pickup_id}`,
    t.operator_job_ref && `job ${t.operator_job_ref}`,
    t.pickup_id && (t.ticket_id ? `scale ticket ${t.ticket_id}` : "no scale ticket shared"),
    t.contract_version_id && `contract version ${t.contract_version_id}`,
    lines,
  ]
    .filter(Boolean)
    .join(" → ");
}

export function RowDetails({ row }: { row: TableRow }) {
  return (
    <div className="details">
      {row.material && <p className="label">{material(row.material)}</p>}
      {(row.weight || row.lines.length > 0) && (
        <table className="lines">
          <thead>
            <tr>
              <th scope="col">Charge</th>
              <th scope="col">Should cost</th>
              <th scope="col">Billed</th>
            </tr>
          </thead>
          <tbody>
            {row.weight && (
              <tr>
                <th scope="row">Weight</th>
                <td className="strong">{row.weight.ours}</td>
                <td className="strong">{row.weight.operator}</td>
              </tr>
            )}
            {row.lines.map((l, i) => {
              const ours = l.ours ? partText(l.ours) : { amount: "Not expected", detail: "" };
              const op = partText(l.operator);
              return (
                <tr key={`${l.line_type}-${i}`} className={l.status === "CHECK" ? "line-check" : undefined}>
                  <th scope="row">
                    {l.label}
                    {l.status === "CHECK" && <span className="sub">Check this</span>}
                  </th>
                  <td>
                    <span className="strong">{ours.amount}</span>
                    {ours.detail && <span className="sub">{ours.detail}</span>}
                  </td>
                  <td>
                    <span className="strong">{op.amount}</span>
                    {op.detail && <span className="sub">{op.detail}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <p className="reason">{row.reason}</p>
      {row.causeText && (
        <p className="note">
          <span className="why-key">Likely source:</span> {row.causeText}
        </p>
      )}
      <dl className="sources">
        {row.sources.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
        <div>
          <dt>How sure</dt>
          <dd>{row.confidence}</dd>
        </div>
      </dl>
      <p className="note trail">
        <span className="why-key">Trail:</span> {trailText(row)}
      </p>
    </div>
  );
}
