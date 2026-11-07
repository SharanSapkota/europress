import { request, type Why } from "./invoices";

export type OperatorAction = "NONE" | "REQUEST_TICKETS" | "CORRECT_LINES" | "RENEGOTIATE" | "TENDER";
export type OperatorDecision = "prepare" | "not_now";

export interface Measure {
  key: string;
  label: string;
  value: string;
  status: "GOOD" | "CHECK";
  source: string;
  why: Why;
}

export interface OperatorCard {
  operator_id: string;
  name: string;
  materials: string[];
  pickups: number;
  months: number;
  months_covered: string[];
  enough_data: boolean;
  measures: Measure[];
  status: "GOOD" | "CHECK";
  suggested_action: OperatorAction;
  suggestion: string;
  why: string;
  suggestion_why: Why;
  value_cents: number | null;
  draft: string | null;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
}

export interface Option {
  id: string;
  name: string;
}

export interface Operators {
  customer_id: string | null;
  customer_name: string | null;
  filters: { customer_id: string | null; site_id: string | null; period: string };
  options: { customers: Option[]; sites: Option[]; operators: Option[]; months: string[] };
  months: number;
  periods: string[];
  operators: OperatorCard[];
}

export interface OperatorDecisionResult {
  decision_id: string;
  decision: OperatorDecision;
  created_at: string;
  draft: string | null;
}

export const getOperators = (query: string) => request<Operators>(`/api/operators${query ? `?${query}` : ""}`);

export const postOperatorDecision = (id: string, decision: OperatorDecision, query: string) =>
  request<OperatorDecisionResult>(`/api/operators/${encodeURIComponent(id)}/decision${query ? `?${query}` : ""}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
