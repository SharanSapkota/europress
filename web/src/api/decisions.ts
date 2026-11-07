import { request } from "./invoices";

export interface DecisionEntry {
  decision_id: string;
  item_type: "invoice_item" | "operator";
  item_id: string;
  label: string;
  decision: string;
  text: string;
  suggestion: { action?: string | null; text?: string | null };
  created_at: string;
  user: string;
  undone: boolean;
}

export const getDecisions = (months = 3) => request<DecisionEntry[]>(`/api/decisions?months=${months}`);

export const undoDecision = (id: string) =>
  request<DecisionEntry>(`/api/decisions/${encodeURIComponent(id)}/undo`, { method: "POST" });
