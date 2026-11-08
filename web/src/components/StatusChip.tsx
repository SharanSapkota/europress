import type { Status } from "../api/invoices";
import { Chip, type ChipTone } from "./ui";

const TEXT: Record<Status, string> = {
  CHECK: "Check this",
  EXPLAINED: "Explained",
  NO_DATA: "Not enough data",
  MATCH: "Matches",
  DISPUTED: "Disputed",
};

const TONE: Record<Status, ChipTone> = { CHECK: "check", EXPLAINED: "neutral", NO_DATA: "neutral", MATCH: "good", DISPUTED: "disputed" };

export function StatusChip({ status }: { status: Status }) {
  return <Chip tone={TONE[status]}>{TEXT[status]}</Chip>;
}
