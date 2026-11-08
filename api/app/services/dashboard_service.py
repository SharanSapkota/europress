from collections import defaultdict

from app.core.config import Settings
from app.services.cards import eur
from app.services.comparison_service import ComparisonService
from app.services.cost_service import CostService
from app.services.feature_data import FeatureData, site_label
from app.services.fleet_service import FleetService
from app.services.pickups_service import PickupsService

LINKS = {"pickups.min_charge_guard": "/containers", "fleet.right_size": "/fleet"}


def tonnes_dot(kg: float) -> str:
    return f"{kg / 1000:.1f} t"


class DashboardService:
    def __init__(self, comparison: ComparisonService, costs: CostService, pickups: PickupsService, fleet: FleetService,
                 data: FeatureData, settings: Settings, customer_sites=None):
        self.comparison = comparison
        self.costs = costs
        self.pickups = pickups
        self.fleet = fleet
        self.data = data
        self.s = settings
        self.customer_sites = customer_sites

    def customers(self) -> list[dict]:
        repo = self.comparison.customers
        return [{"id": c["customer_id"], "name": c.get("customer_name") or c["customer_id"]}
                for c in (repo.all() if repo else [])]

    def tiles(self, customer_id: str, res: dict | None) -> list[dict]:
        views = (res or {}).get("view_counts") or {}
        cost = self.costs.costs(customer_id=customer_id)
        weighted = [(c["ratio"], c["pickups_with_weight"]) for c in cost["containers"] if c["ratio"] is not None]
        n = sum(w for _, w in weighted)
        ratio = round(sum(r * w for r, w in weighted) / n, 1) if n else None
        to_check = views.get("check", 0)
        return [
            {"key": "to_check", "label": "Lifts to check", "value": to_check, "unit": "", "signed": False,
             "status": "CHECK" if to_check else "OK", "link": "/invoices"},
            {"key": "disputed", "label": "Disputed", "value": views.get("disputed", 0), "unit": "", "signed": False,
             "status": "OK", "link": "/invoices"},
            {"key": "cost_per_t", "label": "Cost per tonne", "value": ratio, "unit": "×", "signed": False,
             "status": "CHECK" if ratio is not None and ratio >= self.s.cost_ratio_check else "OK", "link": "/costs"},
        ]

    def candidates(self, customer_id: str) -> list[dict]:
        d = self.data.load(customer_id)
        current = self.pickups.decisions.decisions.current("feature", list(LINKS))
        decided = {k: (v or {}).get("decision") for k, v in current.items()}
        out = []
        guard = self.pickups.min_charge(customer_id)
        by_device: dict[str, list[dict]] = defaultdict(list)
        for t in guard["could_wait"]:
            by_device[t["device_id"]].append(t)
        if by_device and not decided.get("pickups.min_charge_guard"):
            did, items = max(by_device.items(), key=lambda kv: sum(t["topup_cents"] for t in kv[1]))
            dev = d["devices"].get(did) or {}
            saved = sum(t["topup_cents"] for t in items)
            material = (dev.get("material_stream") or "waste").replace("_", " ")
            out.append({"id": "pickups.min_charge_guard", "value_cents": saved, "per_year": saved * 12 / guard["months"],
                        "sentence": f"Order {material} at {site_label(FeatureData.site_name(d, did))} by weight "
                                    f"({tonnes_dot(max(t['breakeven_kg'] for t in items))}), not by fill.",
                        "estimate": f"Saves about {eur(saved)} in minimum charge top-ups every {guard['months']} "
                                    f"months (estimate)."})
        fits = self.fleet.right_size(customer_id)["fits"]
        if fits and not decided.get("fleet.right_size"):
            best = max(fits, key=lambda o: o["saving_cents"])
            dev = d["devices"].get(best["device_id"]) or {}
            material = (dev.get("material_stream") or "waste").replace("_", " ")
            out.append({"id": "fleet.right_size", "value_cents": best["saving_cents"], "per_year": best["saving_cents"],
                        "sentence": f"Move {material} at {site_label(best['site'])} from {best['volume']:g} to "
                                    f"{best['bigger']:g} m³ containers.",
                        "estimate": f"Saves about {eur(best['saving_cents'])} a year after the extra lease (estimate)."})
        return [c for c in out if c["value_cents"] > 0]

    def next_decision(self, customer_id: str) -> dict | None:
        best = max(self.candidates(customer_id), key=lambda c: c["per_year"], default=None)
        if not best:
            return None
        return {"id": best["id"], "sentence": best["sentence"], "estimate": best["estimate"],
                "link": LINKS[best["id"]], "value_cents": best["value_cents"]}

    def dashboard(self, customer_id: str | None = "all", period: str | None = None) -> dict:
        cid = customer_id or "all"
        everyone = cid == "all"
        periods = self.comparison.periods()
        period = period if period in periods else (periods[-1] if periods else None)
        res = self.comparison.compare(period, None if everyone else cid, everyone) if period else None
        sites = self.customer_sites.all() if self.customer_sites else []
        return {"customer_id": cid,
                "customer_name": self.comparison.names([], [], self.comparison.customer_id(
                    None if everyone else cid))["customer_name"],
                "sites": [{"id": x["site_id"], "name": site_label(x.get("site_name")) or x["site_id"]} for x in sites],
                "operator_count": len(res["operator_ids"]) if res else 0,
                "period": period, "periods": periods,
                "totals": res["totals"] if res else None, "why": res["why"] if res else {},
                "tiles": self.tiles(cid, res), "next_decision": self.next_decision(cid)}
