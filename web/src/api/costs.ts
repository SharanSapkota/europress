import { request, type Why } from "./invoices";

export interface Breakdown {
  pickup_fees_cents: number;
  weight_fees_cents: number;
  other_charges_cents: number;
  material_credit_cents: number;
}

export interface Container {
  device_id: string;
  contract_id: string;
  material: string | null;
  name: string;
  full_name: string;
  site_name: string | null;
  cost_per_t_cents: number | null;
  benchmark_cents_per_t: number | null;
  ratio: number | null;
  ratio_label: string | null;
  status: "CHECK" | "NORMAL";
  pickups: number;
  pickups_with_weight: number;
  confidence: "sure" | "not sure yet";
  breakdown: Breakdown;
  estimate: boolean;
  main_reason: string;
  weight_sources: { ticket: number; invoice: number; device: number };
  sources_text: string;
  contract_version_id: string | null;
  why: Record<
    "cost_per_t" | "benchmark" | "ratio" | "pickups" | "pickup_fees" | "weight_fees" | "material_credit" | "main_reason",
    Why
  >;
}

export interface Costs {
  customer_id: string | null;
  customer_name: string | null;
  site_names: string[];
  months: number;
  periods: string[];
  headline: string;
  containers: Container[];
}

export const getCosts = (months = 3) => request<Costs>(`/api/costs?months=${months}`);
