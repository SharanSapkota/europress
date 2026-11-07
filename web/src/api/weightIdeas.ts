import { request, type Why } from "./invoices";
import type { OperatorDecision, OperatorDecisionResult, Option } from "./operators";

export interface SortingCandidate {
  item_id: string;
  device_id: string;
  site_id: string;
  site_name: string;
  customer_id: string;
  equipment_class: string;
  volume_m3: number;
  lifts_count: number;
  total_mass_kg: number;
  measured_density_kg_m3: number;
  nominal_density_kg_m3: number;
  estimated_recyclable_kg: number;
  annual_saving_cents: number;
  status: "CHECK" | "GOOD";
  europress_hardware: string;
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface ResidualPickupRow {
  item_id: string;
  pickup_id: string;
  device_id: string;
  site_id: string;
  site_name: string;
  date: string | null;
  material: string;
  equipment_class: string;
  pickup_status: string;
  mass_before_kg: number;
  mass_after_kg: number;
  residual_pct: number;
  fill_after_pct: number;
  classification: "PHYSICAL_RESIDUAL" | "FROZEN_BIOWASTE_RISK" | "CALIBRATION_OFFSET";
  classification_label: string;
  wasted_capacity_cents: number;
  europress_service: string;
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface CombinedLoadPair {
  item_id: string;
  weighing_event_id: string;
  date: string | null;
  operator_id: string;
  material: string;
  truck_net_kg: number;
  pickup_a_id: string;
  device_a_id: string;
  site_a_name: string;
  device_a_kg: number;
  naive_a_kg: number;
  proportional_a_kg: number;
  pickup_b_id: string;
  device_b_id: string;
  site_b_name: string;
  device_b_kg: number;
  naive_b_kg: number;
  proportional_b_kg: number;
  shift_kg: number;
  shift_pct: number;
  reallocated_value_cents: number;
  status: "CHECK" | "GOOD";
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface PrimaryIdeas {
  customer_id: string | null;
  customer_name: string | null;
  customers: Option[];
  why: Record<string, Why>;
  idea5_sorting: SortingCandidate[];
  idea3_residual: ResidualPickupRow[];
  idea6_combined: CombinedLoadPair[];
}

export interface MinChargeAndMassRow {
  item_id: string;
  device_id: string;
  site_name: string;
  material: string;
  collection_policy: string;
  min_charge_lifts: number;
  min_charge_topup_cents: number;
  break_even_mass_kg: number;
  median_mass_before_kg: number;
  candidate_actions: string;
  max_days: number | null;
  annual_saving_cents: number;
  status: "CHECK" | "GOOD";
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface Day0AndCreditRow {
  item_id: string;
  contract_id: string;
  contract_version_id: string;
  device_id: string;
  site_name: string;
  operator_id: string;
  material: string;
  credit_eligible: boolean;
  credit_share_bp: number;
  unshared_or_delayed_lifts: number;
  weight_gap_lifts: number;
  provisional_receipt_kg: number;
  unlocked_annual_cents: number;
  status: "CHECK" | "GOOD";
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface BipartiteDeconvRow {
  item_id: string;
  source_side: "HAULER_STORED_TARE" | "COMPACTOR_SENSOR_CALIBRATION";
  source_label: string;
  entity_id: string;
  operator_or_site: string;
  lifts_or_orders: number;
  stored_tare_kg: number | null;
  weighed_tare_kg: number | null;
  avg_weight_gap_kg: number;
  financial_impact_cents: number;
  europress_action: string;
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface RightSizerRow {
  item_id: string;
  device_id: string;
  site_name: string;
  material: string;
  equipment_class: string;
  volume_m3: number;
  lifts_count: number;
  compaction_work_orders: number;
  measured_density_kg_m3: number;
  upgrade_path: string;
  customer_annual_saving_cents: number;
  europress_annual_revenue_cents: number;
  suggestion: string;
  reason: string;
  trail_text: string;
  decision: OperatorDecision | null;
  decision_id: string | null;
  decided_at: string | null;
  draft: string | null;
  why: Record<string, Why>;
}

export interface ServiceTier {
  tier_id: string;
  name: string;
  price_eur_month: number;
  target_segment: string;
  included_ideas: string;
  customer_net_roi: string;
  why: Why;
}

export interface SensitivityScenario {
  scenario: string;
  adoption_pct: number;
  realisation_pct: number;
  sensor_noise_pct: number;
  customer_net_benefit_cents: number;
  europress_arr_cents: number;
  europress_net_margin_cents: number;
  payback_months: number;
  why: Why;
}

export interface BusinessCaseBlock {
  cost_to_serve_cents_month: number;
  payback_months: number;
  fleet_devices_total: number;
  fleet_weighed_devices: number;
  tiers: ServiceTier[];
  sensitivity: SensitivityScenario[];
  why: Record<string, Why>;
}

export interface SecondaryIdeas {
  customer_id: string | null;
  customer_name: string | null;
  customers: Option[];
  why: Record<string, Why>;
  idea1_mass_trigger: MinChargeAndMassRow[];
  idea2_day0_receipt: Day0AndCreditRow[];
  idea4_deconvolution: BipartiteDeconvRow[];
  idea7_rightsizer: RightSizerRow[];
  business_case: BusinessCaseBlock;
}

export const getPrimaryIdeas = (customerId: string) =>
  request<PrimaryIdeas>(`/api/weight-ideas/primary?customer_id=${encodeURIComponent(customerId || "all")}`);

export const getSecondaryIdeas = (customerId: string) =>
  request<SecondaryIdeas>(`/api/weight-ideas/secondary?customer_id=${encodeURIComponent(customerId || "all")}`);

export const postIdeaDecision = (itemId: string, decision: OperatorDecision, customerId: string) =>
  request<OperatorDecisionResult>(
    `/api/weight-ideas/${encodeURIComponent(itemId)}/decision?customer_id=${encodeURIComponent(customerId || "all")}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    },
  );
