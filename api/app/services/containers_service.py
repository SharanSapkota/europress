from statistics import median

from app.core.config import Settings
from app.services.cards import eur
from app.services.comparison_service import short_day
from app.services.cost_service import material_name
from app.services.explain import why
from app.services.feature_data import FeatureData, site_label, ts
from app.services.pickups_service import PickupsService

SKIP_SHARE = 0.5
SENSOR_PCT = 5
SENSOR_PAIRS = 3
MIN_SKIP_PER_MONTH = 0.5


def current_rule(dev: dict) -> str:
    policy = dev.get("collection_policy")
    if policy == "FIXED_SCHEDULE":
        return f"Fixed, {dev.get('fixed_schedule_per_week') or '?'} per week"
    if policy == "HYBRID":
        return f"Fixed, skip under {dev.get('hybrid_skip_below_pct') or 0:g} % full"
    return f"Order at {dev.get('on_call_threshold_pct') or 0:g} % full"


def tonnes_dot(kg: float) -> str:
    return f"{kg / 1000:.1f} t"


class ContainersService:
    def __init__(self, data: FeatureData, pickups: PickupsService, decisions, settings: Settings):
        self.data = data
        self.pickups = pickups
        self.decisions = decisions
        self.s = settings

    def _base(self, d: dict, did: str, kind: str, key: str) -> dict:
        dev = d["devices"].get(did) or {}
        return {"id": f"containers.{key}:{did}", "kind": kind, "device_id": did,
                "material": material_name(dev.get("material_stream")),
                "site": site_label(FeatureData.site_name(d, did)), "old_rule": current_rule(dev), "new_rule": None,
                "estimate": None, "estimate_note": None, "value_cents": 0, "fill": None, "sensor": None,
                "highlight": False, "why": None, "decision": None}

    def order_by_weight(self, d: dict, customer_id: str | None) -> list[dict]:
        guard = self.pickups.min_charge(customer_id)
        by_device: dict[str, list[dict]] = {}
        for t in guard["could_wait"]:
            by_device.setdefault(t["device_id"], []).append(t)
        out = []
        for did, items in by_device.items():
            saved = sum(t["topup_cents"] for t in items)
            target = max(t["breakeven_kg"] for t in items)
            now = [x for x in d["daily"] if x["device_id"] == did and x.get("mass_kg_last_valid") is not None]
            now_kg = max(now, key=lambda x: x["date"])["mass_kg_last_valid"] if now else None
            c = self._base(d, did, "rule", "weight")
            c.update(new_rule=f"Order at {tonnes_dot(target)}", estimate=f"≈ {eur(saved)}",
                     estimate_note=f"fewer top-ups / {guard['months']} months", value_cents=saved,
                     fill={"now_kg": now_kg, "target_kg": round(target)} if now_kg is not None else None,
                     why=why(f"About {eur(saved)} of minimum charge top-ups in {guard['months']} months (estimate).",
                             f"Minimum charge top-ups on {len(items)} pickups; contract break-even {round(target)} kg",
                             "medium",
                             f"{len(items)} light pickups could have waited until the container held "
                             f"{tonnes_dot(target)}. Each one stays within the {items[0]['max_days']}-day limit and "
                             f"your site opening days."))
            out.append(c)
        return out

    def skip_light(self, d: dict) -> list[dict]:
        out = []
        for did, ps in FeatureData.lifts_by_device(d).items():
            dev = d["devices"].get(did) or {}
            if dev.get("collection_policy") not in ("FIXED_SCHEDULE", "HYBRID"):
                continue
            rows = [d["rows"].get(p["collection_id"]) for p in ps]
            masses = [r["weight_kg"] for r in rows if r and r["weight_kg"]]
            if len(masses) < 6:
                continue
            threshold = round(median(masses) * SKIP_SHARE / 100) * 100
            max_days = int((d["materials"].get(dev.get("material_stream")) or {}).get("max_days_between_collections") or 28)
            skippable, lift_cents = 0, []
            for prev, p, nxt, r in zip(ps, ps[1:], ps[2:], rows[1:]):
                if not r or not r["weight_kg"] or r["weight_kg"] >= threshold:
                    continue
                gap = (ts(nxt["actual_at"]) - ts(prev["actual_at"])).total_seconds() / 86400
                if gap <= max_days:
                    skippable += 1
                    lift_cents.append(sum(ln["amount_cents"] for ln in r["our_lines"] if ln["line_type"] == "LIFT_FEE"))
            per_month = skippable / d["months"]
            if per_month < MIN_SKIP_PER_MONTH:
                continue
            c = self._base(d, did, "rule", "skip")
            c.update(new_rule=f"Skip when under {tonnes_dot(threshold)}", estimate=f"≈ {round(per_month)}",
                     estimate_note="fewer pickups / month",
                     value_cents=round(per_month * 12 * (sum(lift_cents) / len(lift_cents) if lift_cents else 0)),
                     why=why(f"About {round(per_month)} fewer pickups a month (estimate).",
                             f"{skippable} scheduled pickups under {tonnes_dot(threshold)} in {d['months']} months",
                             "medium",
                             f"A pickup is only skipped when the next one still comes within the {max_days}-day "
                             f"limit; site closures keep their scheduled pickups."))
            out.append(c)
        return out

    def sensor(self, d: dict) -> list[dict]:
        pairs: dict[str, list[tuple[str, float]]] = {}
        for r in d["rows"].values():
            if r.get("device_kg") and r.get("ticket_kg") and r["ticket_kg"] > 0 and r.get("date"):
                pairs.setdefault(r["device_id"], []).append((r["date"], 100 * (r["device_kg"] - r["ticket_kg"]) / r["ticket_kg"]))
        out = []
        for did, items in pairs.items():
            items.sort()
            recent = [x for _, x in items[-5:]]
            if len(recent) < SENSOR_PAIRS or abs(median(recent)) < SENSOR_PCT:
                continue
            since = items[-1][0]
            for day_, x in reversed(items):
                if abs(x) < SENSOR_PCT:
                    break
                since = day_
            gap = abs(median(recent))
            c = self._base(d, did, "sensor", "sensor")
            c.update(new_rule="Check the weight sensor", sensor={"text": f"Scale and tickets differ {gap:.0f} %",
                                                                 "since": f"since {short_day(since)}"},
                     value_cents=0,
                     why=why(f"The container scale and the scale tickets differ by {gap:.0f} %.",
                             f"Last {len(recent)} pickups with both a scale ticket and a container weight", "medium",
                             "A difference can come from the sensor, a stored truck weight or a shared truck."))
            out.append(c)
        return out

    def cards(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        rules = sorted(self.order_by_weight(d, customer_id) + self.skip_light(d), key=lambda c: -c["value_cents"])
        sensors = self.sensor(d)
        cards = rules + sensors
        if rules:
            rules[0]["highlight"] = True
        current = self.decisions.current("feature", [c["id"] for c in cards])
        for c in cards:
            c["decision"] = (current.get(c["id"]) or {}).get("decision")
        return {"customer_id": customer_id or "all", "months": d["months"], "cards": cards}

    def decide(self, card_id: str, decision: str, customer_id: str | None = "all") -> dict | None:
        c = next((x for x in self.cards(customer_id)["cards"] if x["id"] == card_id), None)
        if not c:
            return None
        detail = {"weight": "Light pickups with top-ups", "skip": "Light scheduled pickups"}.get(
            card_id.split(".")[1].split(":")[0], (c["sensor"] or {}).get("text", ""))
        action = "Book a sensor check" if c["kind"] == "sensor" else c["new_rule"]
        return self.decisions.record(
            "feature", card_id, decision, f"{c['material']}, {c['site']}",
            {"action": "BOOK_CHECK" if c["kind"] == "sensor" else "APPLY_RULE", "text": action},
            {"value_cents": c["value_cents"]},
            evidence={"device_id": c["device_id"], "old_rule": c["old_rule"], "new_rule": c["new_rule"],
                      "estimate": c["estimate"], "value_cents": c["value_cents"]},
            view={"title": f"{c['material']}, {c['site']}", "detail": detail, "suggestion": action})
