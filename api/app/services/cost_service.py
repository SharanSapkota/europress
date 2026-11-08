from statistics import median

from app.core.config import Settings
from app.services.comparison_service import ComparisonService, label
from app.services.explain import listing, why
from app.services.periods import resolve
from app.services.comparison_service import eur as _eur
from app.services.pricing import LIFT_STATUSES, credit_price_cents_per_t, rhu

PICKUP_FEES = ("LIFT_FEE", "TRANSPORT")
WEIGHT_FEES = ("HAUL_PER_TONNE", "PROCESSING", "REJECTION_REPROCESSING")
SURCHARGES = ("FUEL_SURCHARGE", "REMOTE_SURCHARGE", "EMERGENCY_SURCHARGE", "SIDE_WASTE_FEE", "CANCELLATION_FEE",
              "WASTED_TRIP_FEE", "CONTAMINATION_PENALTY")
SOURCES = {"ticket": "scale tickets", "invoice": "invoices", "device": "device estimates"}
REQUIRED_TRIGGERS = ("MAX_INTERVAL_RULE", "CUSTOMER_REQUEST_PRE_CLOSURE")
HYGIENE_MAX_DAYS = 7


def eur(cents: int) -> str:
    return _eur(cents).replace(" ", "\u00a0")


def site_label(name: str | None) -> str:
    return (name or "").split(" (")[0]


def material_name(m: str | None) -> str:
    return (m or "waste").replace("_", " ").capitalize()


def recent_rows(comparison: ComparisonService, months: int | list[str], customer_id: str | None, everyone: bool = False):
    if isinstance(months, list):
        periods = months
    else:
        periods = comparison.periods()[-months:] if months else comparison.periods()
    rows, results = {}, []
    for p in periods:
        res = comparison.compare(p, customer_id, everyone)
        results.append(res)
        for r in res["rows"]:
            if r["pickup_id"] not in rows or r["invoice_ids"]:
                rows[r["pickup_id"]] = dict(r, period=p)
    return periods, list(rows.values()), results


def breakdown(rows: list[dict]) -> dict[str, int]:
    out = {"pickup_fees_cents": 0, "weight_fees_cents": 0, "other_charges_cents": 0, "material_credit_cents": 0}
    for r in rows:
        for ln in r["our_lines"]:
            t = ln["line_type"]
            key = ("material_credit_cents" if t == "MATERIAL_CREDIT" else "pickup_fees_cents" if t in PICKUP_FEES
                   else "weight_fees_cents" if t in WEIGHT_FEES else "other_charges_cents")
            out[key] += ln["amount_cents"]
    return out


def cost_per_t(rows: list[dict]) -> tuple[int | None, list[dict]]:
    known = [r for r in rows if r["pickup_status"] in LIFT_STATUSES and r["weight_kg"]]
    kg = sum(r["weight_kg"] for r in known)
    collection = sum(r["summary"]["collection_cost_cents"] for r in known)
    return (rhu(collection * 1000, kg) if kg else None), known


class CostService:
    def __init__(self, comparison: ComparisonService, devices, sites, settings: Settings, telemetry=None):
        self.telemetry = telemetry
        self.comparison = comparison
        self.devices = devices
        self.sites = sites
        self.s = settings

    def costs(self, months: int = 3, customer_id: str | None = None, period: str | None = None,
              start: str | None = None, end: str | None = None) -> dict:
        everyone = customer_id == "all"
        cid = None if everyone else self.comparison.customer_id(customer_id)
        chosen = resolve(self.comparison.data_months(), period, start, end) if period or start or end else months
        periods, rows, _ = recent_rows(self.comparison, chosen, cid, everyone)
        return self.summarize(rows, periods, cid)

    def _daily(self, device_ids: list[str], periods: list[str]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        if self.telemetry and periods and device_ids:
            for d in self.telemetry.for_devices(device_ids, periods[0], periods[-1]):
                out.setdefault(d["device_id"], []).append(d)
        return out

    def summarize(self, rows: list[dict], periods: list[str], cid: str | None) -> dict:
        by_device: dict[str, list[dict]] = {}
        for r in rows:
            by_device.setdefault(r["device_id"], []).append(r)
        daily = self._daily(list(by_device), periods)
        containers = [self.container(d, rs, daily.get(d, [])) for d, rs in by_device.items()]
        materials = [c["material"] for c in containers]
        for c in containers:
            shared = materials.count(c["material"]) > 1 and c["site_name"]
            c["full_name"] = f"{c['name']} at {c['site_name']}" if shared else c["name"]
        containers.sort(key=lambda c: (c["ratio"] is None, -(c["ratio"] or 0), c["name"]))
        site_ids = sorted({r["site_id"] for r in rows if r["site_id"]})
        names = self.comparison.names(site_ids, [], cid)
        return {"customer_id": cid, "customer_name": names["customer_name"], "site_names": names["site_names"],
                "site_count": len(site_ids), "months": len(periods), "periods": periods,
                "headline": self.headline(containers), "highlight": self.highlight(containers),
                "containers": containers}

    def highlight(self, containers: list[dict]) -> dict | None:
        top = max((c for c in containers if c["ratio"] is not None), key=lambda c: c["ratio"], default=None)
        if not top:
            return None
        where = f"{top['name']} at {top['site_label']}" if top["site_label"] else top["name"]
        if top["ratio"] < self.s.cost_ratio_check:
            return {"ratio": top["ratio"], "sentence": "All containers are in the normal range of your contract.",
                    "reason": None, "device_id": top["device_id"]}
        return {"ratio": top["ratio"], "device_id": top["device_id"],
                "sentence": f"{where} costs {top['ratio']:.1f} times the normal rate in your contract.",
                "reason": f"Main reason: {top['short_reason']}." if top["short_reason"] else None}

    def headline(self, containers: list[dict]) -> str:
        worst = next((c for c in containers if c["ratio"] is not None), None)
        if not worst:
            return "Not enough weights yet to work out a cost per tonne."
        if worst["ratio"] < self.s.cost_ratio_check:
            return "All containers are in the normal range."
        return f"{worst['full_name']} costs {worst['ratio']:.1f} times the normal rate in your contract."

    def ratio_label(self, ratio: float | None) -> str | None:
        if ratio is None:
            return None
        return "Normal" if ratio < self.s.cost_ratio_check else f"{ratio:.1f}× normal"

    def container(self, device_id: str, rows: list[dict], daily: list[dict] | None = None) -> dict:
        device = self.devices.get(device_id) or {}
        latest = max(rows, key=lambda r: r["date"] or "")
        site = (self.sites.get(latest["site_id"]) or {}) if latest["site_id"] else {}
        per_t, known = cost_per_t(rows)
        lifts = [r for r in rows if r["pickup_status"] in LIFT_STATUSES]
        bench = (latest["version"] or {}).get("target_collection_cost_cents_per_t")
        ratio = round(per_t / bench, 2) if per_t is not None and bench else None
        sources = {k: sum(1 for r in lifts if r["ours"]["weight_source"] == k) for k in SOURCES}
        return {
            "device_id": device_id, "contract_id": latest["contract_id"], "material": latest["material"],
            "name": material_name(latest["material"]), "site_name": site.get("site_name"),
            "site_label": site_label(site.get("site_name")) or None, "short_reason": self.short_reason(rows),
            "cost_per_t_cents": per_t, "benchmark_cents_per_t": bench, "ratio": ratio,
            "ratio_label": self.ratio_label(ratio),
            "status": "CHECK" if ratio is not None and ratio >= self.s.cost_ratio_check else "NORMAL",
            "pickups": len(lifts), "pickups_with_weight": len(known),
            "confidence": "sure" if len(known) >= self.s.sure_min_pickups else "not sure yet",
            "breakdown": breakdown(rows), "estimate": True,
            "main_reason": self.main_reason(rows, device),
            "constraints": self.constraints(rows, device, daily or []),
            "weight_sources": sources,
            "sources_text": self.sources_text(sources, len(lifts) - len(known)),
            "contract_version_id": latest["contract_version_id"],
            "why": self.container_why(rows, known, per_t, bench, ratio, latest, sources, len(lifts), device, daily or []),
        }

    def constraints(self, rows: list[dict], device: dict, daily: list[dict]) -> dict:
        lifts = [r for r in rows if r["pickup_status"] in LIFT_STATUSES]
        low = [r for r in lifts if r["fill_before_pct"] is not None and r["fill_before_pct"] < self.s.low_fill_pct]
        max_days = self.max_days(rows)
        required = [r for r in low if self.required(r, max_days)]
        messages = sum(d.get("n_messages") or 0 for d in daily)
        valid = sum(d.get("n_valid_mass") or 0 for d in daily)
        weighed = bool(device.get("has_weight_measurement"))
        return {"max_days": max_days, "low_fill_pickups": len(low), "required_low_fill_pickups": len(required),
                "hours_full": sum(d.get("hours_full") or 0 for d in daily) if daily else None,
                "valid_reading_pct": round(100 * valid / messages) if weighed and messages else None,
                "pickups_without_ticket": sum(1 for r in lifts if not r["trail"]["ticket_id"]) if lifts and "trail" in lifts[0]
                else None}

    def max_days(self, rows: list[dict]) -> int | None:
        ours = getattr(self.comparison, "ours", None)
        materials = getattr(ours, "materials", None)
        m = (materials.get(rows[0]["material"]) if materials and rows and rows[0]["material"] else None) or {}
        return m.get("max_days_between_collections")

    def required(self, row: dict, max_days: int | None = None) -> bool:
        return row.get("trigger_type") in REQUIRED_TRIGGERS or (max_days is not None and max_days <= HYGIENE_MAX_DAYS)

    def constraint_text(self, c: dict) -> str:
        parts = []
        if c["required_low_fill_pickups"]:
            parts.append(f"{c['required_low_fill_pickups']} of {c['low_fill_pickups']} low-fill pickups were required "
                         f"(the {c['max_days']}-day maximum interval, hygiene or a pre-closure order) and are not counted as a cause")
        elif c["max_days"]:
            parts.append(f"the material may wait at most {c['max_days']} days between pickups")
        if c["hours_full"]:
            parts.append(f"the container was full for {c['hours_full']} hours, so fewer pickups could overflow")
        elif c["hours_full"] == 0:
            parts.append("the container was never full, so the overflow risk of fewer pickups looks low")
        if c["valid_reading_pct"] is not None:
            parts.append(f"{c['valid_reading_pct']}% of device weight readings were valid")
        if c["pickups_without_ticket"]:
            n = c["pickups_without_ticket"]
            parts.append(f"{n} {'pickup has' if n == 1 else 'pickups have'} no scale ticket")
        text = "; ".join(parts)
        return f"{text[0].upper()}{text[1:]}." if text else "No limits found in the data for this container."

    def container_why(self, rows, known, per_t, bench, ratio, latest, sources, n_lifts, device=None, daily=()) -> dict:
        vid = latest["contract_version_id"]
        conf = "not enough data" if per_t is None else ("high" if len(known) >= self.s.sure_min_pickups and
                                                        sources["ticket"] == len(known) else "low")
        weights = "; ".join(f"{SOURCES[k]}: {n}" for k, n in sources.items() if n) or None
        tickets = listing([r["ticket_id"] for r in known if r.get("ticket_id")], "Scale tickets")
        versions = listing([r["contract_version_id"] for r in rows], "Contract versions")
        sure = f"{len(known)} of {n_lifts} pickups have a known weight."
        return {
            "cost_per_t": why(f"Collection cost divided by {sum(r['weight_kg'] for r in known)} kg of known weight.",
                              "; ".join(x for x in (versions, weights) if x), conf, sure),
            "benchmark": why("Normal collection cost per tonne set in your contract.",
                             f"Contract version {vid}" if vid else None, "high" if bench else "not enough data",
                             None, "observed"),
            "ratio": why("Your cost divided by the normal rate.", f"Contract version {vid}; {weights or 'no weights'}",
                         conf, f"{self.ratio_label(ratio) or 'No ratio'}: the threshold is "
                               f"{self.s.cost_ratio_check:g} times normal."),
            "pickups": why(f"{n_lifts} pickups in the period, {len(known)} with a known weight.",
                           tickets or weights, "high" if n_lifts else "not enough data",
                           f"Sure needs {self.s.sure_min_pickups} pickups with a known weight.", "observed"),
            "pickup_fees": why("Lift and transport fees.", versions, "high"),
            "weight_fees": why("Haul, processing and reprocessing fees per tonne.", f"{versions}; {weights or 'no weights'}",
                               conf if per_t is not None else "not enough data"),
            "main_reason": why("The cost that adds the most to your cost per tonne.",
                               "; ".join(x for x in (versions, f"device {latest['device_id']} fill readings",
                                                     "telemetry daily summary" if daily else None) if x),
                               conf, self.constraint_text(self.constraints(rows, device or {}, list(daily)))),
            "material_credit": why("Credit for the material, from the price index and the quality grade.",
                                   versions, "low" if any(not (r.get("price_args") or {}).get("grade") for r in rows)
                                   else "high"),
        }

    def causes(self, rows: list[dict]) -> dict[str, tuple[int, dict]]:
        max_days = self.max_days(rows)
        lifts = [r for r in rows if r["pickup_status"] in LIFT_STATUSES and not self.required(r, max_days)]
        fills = [r["fill_before_pct"] for r in lifts if r["fill_before_pct"] is not None]
        fill = median(fills) if fills else None
        visit = sum(ln["amount_cents"] for r in lifts for ln in r["our_lines"] if ln["line_type"] in PICKUP_FEES)
        low_fill = round(visit * (1 - fill / 100)) if fill is not None and fill < self.s.low_fill_pct else 0
        mins = [ln["amount_cents"] for r in rows for ln in r["our_lines"] if ln["line_type"] == "MIN_CHARGE_TOPUP"]
        extra: dict[str, int] = {}
        for r in rows:
            for ln in r["our_lines"]:
                if ln["line_type"] in SURCHARGES:
                    extra[ln["line_type"]] = extra.get(ln["line_type"], 0) + ln["amount_cents"]
        lost = 0
        for r in lifts:
            args, v = r.get("price_args") or {}, r.get("version")
            if v and args.get("credit_eligible") and r["weight_kg"] and args.get("grade") not in (None, "A"):
                gap = (credit_price_cents_per_t(v, args.get("index_cents"), "A")
                       - credit_price_cents_per_t(v, args.get("index_cents"), args["grade"]))
                lost += rhu(r["weight_kg"] * gap, 1000)
        return {"low_fill": (low_fill, {"fill": fill}), "min_charge": (sum(mins), {"n": len(mins)}),
                "surcharges": (sum(extra.values()), {"top": max(extra, key=extra.get) if extra else None}),
                "low_credit": (lost, {})}

    def short_reason(self, rows: list[dict]) -> str | None:
        cause, (cents, _) = max(self.causes(rows).items(), key=lambda kv: kv[1][0])
        if cents <= 0:
            return None
        return {"low_fill": "pickups when the container is far from full",
                "min_charge": "light pickups that trigger the minimum charge",
                "surcharges": "surcharges and extra fees",
                "low_credit": "a lower material credit because of the quality grade"}[cause]

    def main_reason(self, rows: list[dict], device: dict) -> str:
        cause, (cents, info) = max(self.causes(rows).items(), key=lambda kv: kv[1][0])
        if cents <= 0:
            return "No single cost stands out; the cost follows the rates in your contract."
        if cause == "low_fill":
            schedule = " on a fixed schedule" if device.get("collection_policy") == "FIXED_SCHEDULE" else ""
            return (f"Pickups happen at about {round(info['fill'])}% full{schedule}, so you pay a pickup fee "
                    f"for little waste.")
        if cause == "min_charge":
            return (f"A minimum charge was added on {info['n']} pickups because the loads were lighter than the "
                    f"contract minimum ({eur(cents)}, estimate).")
        if cause == "surcharges":
            return f"Surcharges and extra fees add {eur(cents)} (estimate), mostly the {label(info['top']).lower()}."
        return (f"Material credit is {eur(cents)} lower than at grade A because of the quality grades "
                f"(estimate).")

    @staticmethod
    def sources_text(sources: dict, unknown: int) -> str:
        parts = [f"{SOURCES[k]} ({n} pickups)" for k, n in sources.items() if n]
        text = f"Weights from {' and '.join(parts)}." if parts else "No weights known yet."
        if unknown:
            text += f" {unknown} pickups without a known weight are left out."
        return f"{text} Prices from your contract."
