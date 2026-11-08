import { Fragment, useState } from "react";
import type { Decision, LineComparison, Status, Trail, View, Why as WhyInfo } from "../api/invoices";
import { day, eur, material as materialName, signedEur } from "../format";
import { MessageModal } from "./MessageModal";
import { RowDetails } from "./RowDetails";
import { Chip, DataTable, InfoIcon, TableHeader } from "./ui";

export interface TableRow {
  id: string;
  date: string | null;
  material: string | null;
  ours: { amount: number | null; note: string; why?: WhyInfo };
  operator: { amount: number; note: string };
  difference: number;
  status: Status;
  view: View;
  reason: string;
  shortReason: string | null;
  confidence: string;
  sources: [string, string][];
  weight: { ours: string; operator: string } | null;
  lines: LineComparison[];
  decision: Decision | null;
  disputedAt: string | null;
  causeText: string | null;
  trail: Trail;
  dispute: { invoiceId: string | null; message: string; pickup: boolean };
}

interface Props {
  rows: TableRow[];
  restRows: TableRow[];
  counts: { match: number; explained: number };
  onQuestion: (row: TableRow, message: string) => Promise<void>;
}

const COLS = 5;

function DisputeModal({ row, onClose, onSave }: { row: TableRow; onClose: () => void; onSave: (message: string) => Promise<void> }) {
  const sub = [row.dispute.invoiceId && `Invoice ${row.dispute.invoiceId}`, row.material && materialName(row.material), day(row.date)]
    .filter(Boolean)
    .join(" · ");
  return (
    <MessageModal
      id={row.id}
      title="Dispute this lift"
      sub={sub}
      strip={[
        { label: "Should cost", value: row.ours.amount === null ? "–" : eur(row.ours.amount) },
        { label: "Billed", value: eur(row.operator.amount) },
        { label: "Difference", value: signedEur(row.difference), check: true },
      ]}
      message={row.dispute.message}
      subject={`Invoice ${row.dispute.invoiceId ?? ""}: please check the lift on ${day(row.date)}`}
      onClose={onClose}
      onSave={onSave}
    />
  );
}

export function ComparisonTable({ rows, restRows, counts, onQuestion }: Props) {
  const [open, setOpen] = useState<string | null>(null);
  const [dispute, setDispute] = useState<TableRow | null>(null);
  const [showRest, setShowRest] = useState(false);

  const action = (r: TableRow) => {
    if (r.view === "disputed")
      return (
        <span className="disputed-cell">
          <Chip tone="disputed">Disputed</Chip>
          {r.disputedAt && <span className="sub-small">Sent {day(r.disputedAt.slice(0, 10))}</span>}
        </span>
      );
    if (r.view !== "check") return null;
    return (
      <button type="button" className="btn btn-primary" onClick={() => setDispute(r)}>
        Submit a dispute
      </button>
    );
  };

  const renderRow = (r: TableRow) => {
    const expanded = open === r.id;
    const detailsId = `details-${r.id}`;
    const flagged = r.view === "check" || r.view === "disputed";
    return (
      <Fragment key={r.id}>
        <tr className={expanded ? "row is-open" : "row"}>
          <td>
            <span className="cell-date">{day(r.date)}</span>
            {r.shortReason && <span className="sub-small">{r.shortReason}</span>}
          </td>
          <td>
            <span className="amount amount-line">
              {r.ours.amount === null ? "–" : eur(r.ours.amount)}
              {r.ours.why && <InfoIcon info={r.ours.why} label={`should cost on ${day(r.date)}`} variant="source" />}
            </span>
            <span className="sub-small">{r.ours.note}</span>
          </td>
          <td>
            <span className={r.view === "disputed" ? "amount disputed-amount" : "amount"}>{eur(r.operator.amount)}</span>
            <span className="sub-small">{r.operator.note}</span>
          </td>
          <td className={flagged ? "amount diff diff-check" : "amount diff"}>{signedEur(r.difference)}</td>
          <td className="action">
            <span className="action-cell">
              {action(r)}
              <button
                type="button"
                className="link link-small"
                aria-expanded={expanded}
                aria-controls={detailsId}
                onClick={() => setOpen(expanded ? null : r.id)}
              >
                {expanded ? "Hide" : "Details"}
              </button>
            </span>
          </td>
        </tr>
        {expanded && (
          <tr className="details-row" id={detailsId}>
            <td colSpan={COLS}>
              <RowDetails row={r} />
            </td>
          </tr>
        )}
      </Fragment>
    );
  };

  return (
    <DataTable>
      {dispute && <DisputeModal row={dispute} onClose={() => setDispute(null)} onSave={(m) => onQuestion(dispute, m)} />}
      <table className="comparison invoices-table">
        <TableHeader cells={["Date", "Should cost", "Billed", "Difference", <span className="visually-hidden">Action</span>]} />
        <tbody>
          {rows.length ? (
            rows.map(renderRow)
          ) : (
            <tr>
              <td colSpan={COLS} className="status-text">
                Nothing to check this month.
              </td>
            </tr>
          )}
        </tbody>
        {restRows.length > 0 && (
          <tbody>
            <tr className="table-foot">
              <td colSpan={COLS}>
                <span className="table-foot-inner">
                  <span className="strong">
                    {counts.match} {counts.match === 1 ? "pickup matches" : "pickups match"} · {counts.explained} explained
                  </span>
                  <button type="button" className="link-small show-more" aria-expanded={showRest} onClick={() => setShowRest(!showRest)}>
                    {showRest ? "Hide" : "Show"}{" "}
                    <span aria-hidden="true">›</span>
                  </button>
                </span>
              </td>
            </tr>
            {showRest && restRows.map(renderRow)}
          </tbody>
        )}
      </table>
    </DataTable>
  );
}
