export type Status = "MATCH" | "CHECK" | "EXPLAINED" | "NO_DATA" | "DISPUTED";
export type Decision = "ok" | "dispute_draft" | "dispute_sent";
export type View = "check" | "disputed" | "explained" | "match";

export interface Why {
  what: string;
  source: string;
  confidence: "high" | "medium" | "low" | "not enough data";
  reason: string | null;
  evidence: "observed" | "estimated" | "simulated" | "hypothetical";
}

export interface DisputeRef {
  invoice_id: string | null;
  line_no: number | null;
  invoice_line_id: string | null;
  operator_email: string | null;
}

export interface Trail {
  pickup_id?: string | null;
  operator_job_ref?: string | null;
  ticket_id?: string | null;
  contract_version_id?: string | null;
  invoice_ids: string[];
  invoice_line_ids: string[];
  device_id?: string | null;
}

export interface LinePart {
  quantity: number | null;
  unit: string | null;
  rate_cents: number | null;
  amount_cents: number;
}

export interface LineComparison {
  line_type: string;
  label: string;
  ours: LinePart | null;
  operator: LinePart | null;
  difference_cents: number;
  duplicate: boolean;
  status: "MATCH" | "CHECK";
  our_source: string | null;
  operator_source: string | null;
  invoice_line_id: string | null;
  why: Why;
}

export interface Item {
  family: string;
  entity_type: "collection" | "invoice_line";
  entity_id: string | null;
  status: Status;
  euros_at_stake_cents: number;
  confidence: string;
  reason: string;
  sources: Record<string, string | null>;
  line_type: string | null;
}

export interface UnmatchedLine extends Item {
  label: string;
  service_date: string | null;
  operator_job_ref: string | null;
  draft_question: string;
  invoice_id: string;
  operator_id: string | null;
  why: Record<string, Why>;
  cause_text: string;
  trail: Trail;
  needs_attention: boolean;
  short_reason: string | null;
  dispute: DisputeRef;
  found_status: Status;
  decision: Decision | null;
  decision_id: string | null;
  decided_at: string | null;
  disputed_at: string | null;
  view: View;
  ours_note: string;
  billed_note: string;
  dispute_message: string;
}

export interface PickupComparison {
  pickup_id: string;
  site_id: string | null;
  operator_id: string | null;
  draft_question: string | null;
  date: string | null;
  material: string | null;
  contract_id: string;
  contract_version_id: string | null;
  device_id: string;
  operator_job_ref: string | null;
  pickup_status: string;
  invoice_ids: string[];
  match_by: "job_ref" | "contract_date_type" | null;
  ours: {
    amount_cents: number;
    weight_kg: number | null;
    weight_source: "ticket" | "invoice" | "device" | null;
    range_kg: number | null;
    confidence: string;
    lower_bound: boolean;
    estimate: boolean;
    cost_per_t_cents: number | null;
  };
  operator: { amount_cents: number; billed_kg: number | null };
  device_kg: number | null;
  ticket_kg: number | null;
  difference_cents: number;
  euros_at_stake_cents: number;
  status: Status;
  reason: string;
  evidence: "strong" | "weak";
  suggested_action: "CORRECT_LINE" | "REQUEST_TICKET" | "NONE";
  sources: Record<string, string | null>;
  why: Record<string, Why>;
  cause_text: string | null;
  trail: Trail;
  needs_attention: boolean;
  short_reason: string | null;
  dispute: DisputeRef;
  found_status: Status;
  items: Item[];
  lines: LineComparison[];
  decision: Decision | null;
  decision_id: string | null;
  decided_at: string | null;
  disputed_at: string | null;
  view: View;
  ours_note: string;
  billed_note: string;
  dispute_message: string;
}

export interface Comparison {
  period: string;
  tolerance_pct: number;
  customer_name: string | null;
  site_ids: string[];
  site_names: string[];
  operator_ids: string[];
  operator_names: string[];
  why: Record<"ours" | "operator" | "difference", Why>;
  attention_count: number;
  match_count: number;
  totals: {
    ours_cents: number;
    operator_cents: number;
    difference_cents: number;
    unmatched_cents: number;
    monthly_fixed_cents: number;
  };
  counts: Record<Status, number>;
  view_counts: Record<View, number>;
  line_counts: Record<"MATCHED" | "DUPLICATE" | "NO_LIFT", number>;
  unmatched_lines: UnmatchedLine[];
  rows: PickupComparison[];
}

export interface DecisionResult {
  decision_id: string;
  decision: Decision;
  created_at: string;
}

export const scope = { customer_id: "", site_id: "" };

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const u = new URL(url, window.location.origin);
  if (scope.customer_id) u.searchParams.set("customer_id", scope.customer_id);
  if (scope.site_id) u.searchParams.set("site_id", scope.site_id);
  const res = await fetch(u.pathname + u.search, init);
  if (!res.ok) throw new Error(`${res.status}`);
  return (await res.json()) as T;
}

export const getPeriods = () => request<string[]>("/api/invoices/periods");

export const getComparison = (period: string) =>
  request<Comparison>(`/api/invoices/comparison?period=${encodeURIComponent(period)}`);

export const postQuestion = (id: string, message: string, pickup: boolean) =>
  request<DecisionResult>(`/api/invoices/${pickup ? "comparison" : "items"}/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision: "question", message }),
  });

export const postDecision = (id: string, decision: Decision | "question") =>
  request<DecisionResult>(`/api/invoices/items/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
