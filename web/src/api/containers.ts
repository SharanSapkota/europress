import { request, type Why } from "./invoices";

export interface ContainerCard {
  id: string;
  kind: "rule" | "sensor";
  device_id: string;
  material: string;
  site: string;
  old_rule: string;
  new_rule: string | null;
  estimate: string | null;
  estimate_note: string | null;
  value_cents: number;
  fill: { now_kg: number; target_kg: number } | null;
  sensor: { text: string; since: string } | null;
  highlight: boolean;
  why: Why | null;
  decision: string | null;
}

export interface Containers {
  customer_id: string;
  months: number;
  cards: ContainerCard[];
}

export const getContainers = () => request<Containers>("/api/containers");

export const postContainerDecision = (id: string, decision: "approve" | "not_now" | "prepare") =>
  request(`/api/containers/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision }),
  });
