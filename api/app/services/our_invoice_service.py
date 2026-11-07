from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.services.pricing import LIFT_STATUSES, price_event, summarize

EXECUTED = ("COMPLETED", "PARTIAL", "WASTED_TRIP")


def local_service_date(pickup: dict, tz: str) -> str | None:
    ts = pickup.get("actual_at") if pickup["status"] in EXECUTED else None
    ts = ts or pickup.get("scheduled_at")
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ZoneInfo(tz)).date().isoformat()


def invoice_tonnage(op_lines: list[dict]) -> dict | None:
    return next((ln for ln in op_lines or [] if ln.get("unit") == "t" and ln.get("quantity") is not None
                 and ln.get("match_status", "MATCHED") == "MATCHED"), None)


class OurInvoiceService:
    def __init__(self, devices, tickets, quality, contracts, versions, price_index, materials, settings: Settings):
        self.devices = devices
        self.tickets = tickets
        self.quality = quality
        self.contracts = contracts
        self.versions = versions
        self.price_index = price_index
        self.materials = materials
        self.s = settings

    def version_on(self, contract_id: str, day: str) -> dict | None:
        for v in self.versions.for_contract(contract_id):
            if v["effective_from"] <= day and (v.get("effective_to") is None or day < v["effective_to"]):
                return v
        return None

    def device_kg(self, pickup: dict, device: dict | None) -> int | None:
        est = pickup.get("device_estimated_collected_kg")
        if device and device.get("has_weight_measurement") and est is not None and est >= 0:
            return round(est)
        return None

    def weight(self, pickup: dict, ticket: dict | None, device: dict | None, op_lines: list[dict]) -> dict:
        if ticket and ticket.get("allocated_net_kg") is not None:
            return {"kg": max(0, int(ticket["allocated_net_kg"])), "source": "ticket", "range_kg": 0,
                    "source_id": ticket["ticket_id"], "confidence": "high"}
        inv = invoice_tonnage(op_lines)
        if inv:
            return {"kg": round(inv["quantity"] * 1000), "source": "invoice", "range_kg": 0,
                    "source_id": inv["invoice_line_id"], "confidence": "medium"}
        kg = self.device_kg(pickup, device)
        if kg is not None:
            return {"kg": kg, "source": "device", "range_kg": round(kg * self.s.device_range_pct / 100),
                    "source_id": pickup["device_id"], "confidence": "medium"}
        return {"kg": None, "source": None, "range_kg": None, "source_id": None, "confidence": "Not enough data"}

    def for_pickup(self, pickup: dict, op_lines: list[dict] | None = None) -> dict:
        day = local_service_date(pickup, self.s.local_tz)
        device = self.devices.get(pickup["device_id"])
        contract = self.contracts.get(pickup["contract_id"]) or {}
        material = (device or {}).get("material_stream") or contract.get("material_stream")
        credit_eligible = bool((self.materials.get(material) or {}).get("credit_eligible"))
        ticket = self.tickets.by_job_ref(pickup["operator_job_ref"]) if pickup.get("operator_job_ref") else None
        weight = self.weight(pickup, ticket, device, op_lines or [])
        qa = self.quality.by_ticket(ticket["ticket_id"]) if ticket else None
        grade = (qa or {}).get("grade") or ("A" if credit_eligible else None)
        version = self.version_on(pickup["contract_id"], day) if day else None
        index_cents = None
        if contract.get("price_index_id") and day:
            idx = self.price_index.price(contract["price_index_id"], day[:7])
            index_cents = round(idx["price_eur_per_t"] * 100) if idx else None
        trigger = pickup.get("trigger_type")
        if trigger == "RESCHEDULED":
            trigger = pickup.get("original_trigger_type")
        args = dict(grade=grade, index_cents=index_cents, emergency=trigger == "AD_HOC_CUSTOMER",
                    side_waste=bool(pickup.get("driver_reported_side_waste")),
                    notice_hours=pickup.get("cancellation_notice_hours"), credit_eligible=credit_eligible)
        lines = price_event(version, pickup["status"], weight["kg"], **args) if version else []
        return {
            "pickup_id": pickup["collection_id"], "device_id": pickup["device_id"],
            "contract_id": pickup["contract_id"],
            "contract_version_id": (version or {}).get("contract_version_id"),
            "version": version, "price_args": args,
            "operator_job_ref": pickup.get("operator_job_ref"),
            "service_date": day, "material": material, "status": pickup["status"],
            "weight": weight, "device_kg": self.device_kg(pickup, device),
            "ticket": ticket, "grade": grade, "grade_source": (qa or {}).get("quality_assessment_id"),
            "lines": lines, "total_cents": sum(ln["amount_cents"] for ln in lines),
            "summary": summarize(lines, weight["kg"]),
            "lower_bound": pickup["status"] in LIFT_STATUSES and weight["kg"] is None,
        }

    def reprice(self, ours: dict, kg: int | None) -> int:
        if not ours["version"]:
            return 0
        return sum(ln["amount_cents"] for ln in price_event(ours["version"], ours["status"], kg, **ours["price_args"]))
