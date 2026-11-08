from collections import defaultdict
from datetime import datetime

from app.services.comparison_service import ComparisonService
from app.services.cost_service import recent_rows
from app.services.pricing import LIFT_STATUSES


def site_label(name: str | None) -> str:
    return (name or "").split(" (")[0]


def ts(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


class FeatureData:
    def __init__(self, comparison: ComparisonService, pickups, tickets, devices, sites, contracts, materials,
                 quality, grade_rules, work_orders, calendar, daily, price_index):
        self.comparison = comparison
        self.pickups = pickups
        self.tickets = tickets
        self.devices = devices
        self.sites = sites
        self.contracts = contracts
        self.materials = materials
        self.quality = quality
        self.grade_rules = grade_rules
        self.work_orders = work_orders
        self.calendar = calendar
        self.daily = daily
        self.price_index = price_index
        self._cache: dict = {}

    def scope(self, customer_id: str | None) -> str | None:
        return None if customer_id in (None, "", "all") else customer_id

    def load(self, customer_id: str | None = "all") -> dict:
        cid = self.scope(customer_id)
        if cid in self._cache:
            return self._cache[cid]
        periods, rows, _ = recent_rows(self.comparison, 0, cid, cid is None)
        pickups = [p for p in self.pickups.all() if not cid or p.get("customer_id") == cid]
        devices = {d["device_id"]: d for d in self.devices.all()}
        sites = {s["site_id"]: s for s in self.sites.all()}
        device_ids = sorted({p["device_id"] for p in pickups})
        daily = self.daily.for_devices(device_ids, periods[0], periods[-1]) if periods and device_ids else []
        data = {
            "customer_id": cid, "periods": periods, "months": max(1, len({r["date"][:7] for r in rows if r["date"]})),
            "rows": {r["pickup_id"]: r for r in rows}, "pickups": pickups, "devices": devices, "sites": sites,
            "materials": {m["material_stream"]: m for m in self.materials.all()},
            "tickets": self.tickets.all(), "quality": self.quality.all(),
            "grades": {g["grade"]: float(g["credit_quality_factor"]) for g in self.grade_rules.all()},
            "work_orders": [w for w in self.work_orders.all() if w["device_id"] in set(device_ids)],
            "calendar": {(c["site_id"], c["date"]): c for c in self.calendar.all()},
            "daily": daily, "contracts": {c["contract_id"]: c for c in self.contracts.all()},
            "index": {(p["index_id"], p["month"]): p for p in self.price_index.all()},
            "by_job": {p.get("operator_job_ref"): p for p in pickups if p.get("operator_job_ref")},
        }
        self._cache[cid] = data
        return data

    @staticmethod
    def site_name(data: dict, device_id: str) -> str | None:
        dev = data["devices"].get(device_id) or {}
        return (data["sites"].get(dev.get("site_id")) or {}).get("site_name") or dev.get("site_id")

    @staticmethod
    def container(data: dict, device_id: str) -> str:
        dev = data["devices"].get(device_id) or {}
        material = (dev.get("material_stream") or "waste").replace("_", " ").capitalize()
        return f"{material} · {site_label(FeatureData.site_name(data, device_id))}"

    @staticmethod
    def lifts_by_device(data: dict) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = defaultdict(list)
        for p in data["pickups"]:
            if p["status"] in LIFT_STATUSES and p.get("actual_at"):
                out[p["device_id"]].append(p)
        for ps in out.values():
            ps.sort(key=lambda p: p["actual_at"])
        return out


class FeatureDecisions:
    def __init__(self, decisions):
        self.decisions = decisions

    def apply(self, cards: list[dict]) -> list[dict]:
        current = self.decisions.current("feature", [c["id"] for c in cards])
        for c in cards:
            d = current.get(c["id"]) or {}
            c["decision"], c["decision_id"], c["decided_at"] = d.get("decision"), d.get("decision_id"), d.get("created_at")
        return cards

    def record(self, cards: list[dict], card_id: str, decision: str) -> dict | None:
        c = next((c for c in cards if c["id"] == card_id), None)
        if not c or not c["actions"]:
            return None
        numbers = {n["label"]: n["value"] for n in (c["example"] or {}).get("numbers", [])}
        return self.decisions.record("feature", card_id, decision, c["title"],
                                     {"action": "PREPARE_PROPOSAL", "text": c["explanation"]}, numbers)
