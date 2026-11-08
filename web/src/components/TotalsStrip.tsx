import type { Comparison } from "../api/invoices";
import { eur, signedEur } from "../format";
import { TotalsPanel } from "./ui";

export function TotalsStrip({ totals, why }: { totals: Comparison["totals"]; why: Comparison["why"] }) {
  return (
    <TotalsPanel
      items={[
        { label: "Should cost (estimate)", value: eur(totals.ours_cents), info: why.ours },
        { label: "Billed", value: eur(totals.operator_cents), info: why.operator },
        { label: "Difference", value: signedEur(totals.difference_cents), info: why.difference },
      ]}
    />
  );
}
