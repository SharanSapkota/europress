import { request, type Why } from "./invoices";

export interface Plan {
  key: string;
  name: string;
  price_eur: number | null;
  current: boolean;
  features: string[];
}

export interface ValuePage {
  customer_id: string;
  months: number;
  devices: number;
  value_found_cents: number;
  plan_cost_cents: number;
  net_cents: number;
  why: Record<"found" | "cost", Why>;
  plans: Plan[];
  europress: { adoption_pct: number; containers: number; yearly_eur: number; text: string };
}

export const getValue = () => request<ValuePage>("/api/value");
