import { Fragment, useState } from "react";
import type { Decision, LineComparison, Status, Trail, Why as WhyInfo } from "../api/invoices";
import { day, eur, material, signedEur } from "../format";
import { RowDetails } from "./RowDetails";
import { StatusChip } from "./StatusChip";
import { Why } from "./Why";

export interface TableRow {
  id: string;
  date: string | null;
  material: string | null;
  ours: { amount: number | null; sub: string };
  operator: { amount: number; sub: string };
  difference: number;
  status: Status;
  reason: string;
  confidence: string;
  sources: [string, string][];
  weight: { ours: string; operator: string } | null;
  lines: LineComparison[];
  draft: string | null;
  decision: Decision | null;
  decidedAt: string | null;
  why: Record<string, WhyInfo>;
  causeText: string | null;
  trail: Trail;
}

interface Props {
  rows: TableRow[];
  matchRows: TableRow[];
  onDecide: (id: string, decision: Decision) => Promise<void>;
}

export const DECISION_TEXT: Record<Decision, string> = {
  ok: "Marked as OK",
  dispute_draft: "Question prepared",
  dispute_sent: "Question sent",
};

export function ComparisonTable({ rows, matchRows, onDecide }: Props) {
  const [open, setOpen] = useState<string | null>(null);
  const [showMatches, setShowMatches] = useState(false);

  const renderRow = (r: TableRow) => {
    const expanded = open === r.id;
    const detailsId = `details-${r.id}`;
    return (
      <Fragment key={r.id}>
        <tr className={expanded ? "row is-open" : "row"}>
          <td className="muted">{day(r.date)}</td>
          <td className="strong">{material(r.material)}</td>
          <td>
            <span className="amount">
              {r.ours.amount === null ? "–" : eur(r.ours.amount)}
              {r.ours.amount !== null && <Why info={r.why.ours} label="our invoice" />}
            </span>
            <span className="sub">{r.ours.sub}</span>
          </td>
          <td>
            <span className="amount">
              <span className={r.status === "DISPUTED" ? "disputed-amount" : undefined}>{eur(r.operator.amount)}</span>
              <Why info={r.why.operator} label="operator invoice" />
            </span>
            <span className="sub">{r.operator.sub}</span>
          </td>
          <td className="amount">
            {signedEur(r.difference)}
            <Why info={r.why.difference} label="difference" />
          </td>
          <td>
            <StatusChip status={r.status} />
            {r.decision && <span className="decision">{DECISION_TEXT[r.decision]}</span>}
          </td>
          <td className="action">
            <button
              type="button"
              className="link"
              aria-expanded={expanded}
              aria-controls={detailsId}
              onClick={() => setOpen(expanded ? null : r.id)}
            >
              {expanded ? "Hide" : "Details"}
            </button>
          </td>
        </tr>
        {expanded && (
          <tr className="details-row" id={detailsId}>
            <td colSpan={7}>
              <RowDetails row={r} onDecide={onDecide} />
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  return (
    <div className="table-box">
      <table className="comparison">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Material</th>
            <th scope="col">Our invoice</th>
            <th scope="col">Operator invoice</th>
            <th scope="col">Difference</th>
            <th scope="col">Status</th>
            <th scope="col"><span className="visually-hidden">Details</span></th>
          </tr>
        </thead>
        <tbody>{rows.map(renderRow)}</tbody>
        {matchRows.length > 0 && (
          <tbody>
            <tr className="match-toggle">
              <td colSpan={7}>
                <button type="button" className="toggle" aria-expanded={showMatches} onClick={() => setShowMatches(!showMatches)}>
                  <span aria-hidden="true">{showMatches ? "▾" : "▸"}</span> {matchRows.length}{" "}
                  {matchRows.length === 1 ? "pickup matches" : "pickups match"}
                </button>
              </td>
            </tr>
            {showMatches && matchRows.map(renderRow)}
          </tbody>
        )}
      </table>
      {[...rows, ...matchRows].some((r) => r.status === "DISPUTED") && (
        <p className="note">Underlined amounts are disputed: you told us you sent the question to the operator.</p>
      )}
    </div>
  );
}
