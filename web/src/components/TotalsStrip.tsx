import type { Comparison } from "../api/invoices";
import { eur, signedEur } from "../format";
import { Why } from "./Why";

export function TotalsStrip({ totals, why }: { totals: Comparison["totals"]; why: Comparison["why"] }) {
  return (
    <dl className="totals">
      <div>
        <dt>Our invoice (estimate)</dt>
        <dd>
          {eur(totals.ours_cents)}
          <Why info={why.ours} label="our invoice total" />
        </dd>
      </div>
      <div>
        <dt>Operator invoice</dt>
        <dd>
          {eur(totals.operator_cents)}
          <Why info={why.operator} label="operator invoice total" />
        </dd>
      </div>
      <div>
        <dt>Difference</dt>
        <dd>
          {signedEur(totals.difference_cents)}
          <Why info={why.difference} label="difference" />
        </dd>
      </div>
    </dl>
  );
}
