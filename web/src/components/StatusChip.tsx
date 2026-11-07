import type { Status } from "../api/invoices";

const TEXT: Record<Status, string> = {
  CHECK: "Check this",
  EXPLAINED: "Explained",
  NO_DATA: "Not enough data",
  MATCH: "Matches",
  DISPUTED: "Disputed",
};

export function StatusChip({ status }: { status: Status }) {
  return <span className={`chip chip-${status.toLowerCase()}`}>{TEXT[status]}</span>;
}
