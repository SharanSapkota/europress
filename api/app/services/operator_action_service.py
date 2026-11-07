from datetime import datetime, timedelta, timezone
from statistics import median
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.services.comparison_service import ComparisonService
from app.services.cost_service import recent_rows
from app.services.pricing import LIFT_STATUSES, price_event

FEE_FIELDS = ["lift_fee_cents", "per_km_cents", "fuel_surcharge_bp", "haul_fee_cents_per_t", "processing_fee_cents_per_t",
              "min_charge_cents", "rental_cents_per_month", "contamination_penalty_cents", "rejection_fee_cents_per_t",
              "cancellation_fee_cents", "wasted_trip_fee_cents", "side_waste_fee_cents", "emergency_surcharge_cents"]
LEVELS = (("L1", ("region_code", "material_stream", "pricing_model", "bucket")),
          ("L2", ("region_code", "material_stream", "pricing_model")),
          ("L3", ("material_stream", "pricing_model", "bucket")),
          ("L4", ("material_stream", "pricing_model")))
RECOVERABLE = ("DUPLICATE_LINE", "WRONG_SURCHARGE", "WEIGHT_BASIS_MISMATCH", "OUTDATED_TARIFF", "UNMATCHED_LINE")
ACTIONS = ("DISPUTE_INVOICE", "REQUEST_WEIGHBRIDGE_DATA", "RENEGOTIATE_CONTRACT", "TENDER_OR_SWITCH_OPERATOR")


def ts(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def bucket(volume) -> str:
    v = float(volume or 0)
    return "S" if v <= 8 else ("M" if v <= 16 else "L")


def peer_terms(rows: list[dict], target: dict, min_n: int = 4) -> tuple[dict | None, str | None]:
    for level, cols in LEVELS:
        group = [r for r in rows if all(r[c] == target[c] for c in cols)]
        if len(group) - 1 >= min_n:
            return {f: median(float(r["version"][f] or 0) for r in group) for f in FEE_FIELDS + ["credit_share_bp", "free_km"]}, level
    return None, None


class OperatorActionService:
    def __init__(self, comparison: ComparisonService, contracts, versions, devices, sites, materials, operators,
                 tickets, settings: Settings):
        self.comparison = comparison
        self.contracts = contracts
        self.versions = versions
        self.devices = devices
        self.sites = sites
        self.materials = materials
        self.operators = operators
        self.tickets = tickets
        self.s = settings
        self._data = None

    def _load(self):
        if self._data is None:
            _, rows, results = recent_rows(self.comparison, 0, None, everyone=True)
            invoices = {i["invoice_id"]: i for res in results for i in res["invoices"]}
            items = []
            for r in rows:
                for it in r["items"]:
                    if it["status"] in ("CHECK", "DISPUTED") or r["status"] == "DISPUTED":
                        items.append(dict(it, contract_id=r["contract_id"], operator_id=r["operator_id"],
                                          pickup_id=r["pickup_id"], ticket=r["ticket_kg"] is not None))
            for res in results:
                for u in res["unmatched_lines"]:
                    inv = invoices.get(u["invoice_id"], {})
                    items.append(dict(u, contract_id=inv.get("contract_id"), pickup_id=None, ticket=False))
            tickets = {t["operator_job_ref"]: t for t in self.tickets.all() if t.get("operator_job_ref")}
            self._data = {"rows": rows, "invoices": invoices, "items": items, "tickets": tickets,
                          "start": min((r["date"] for r in rows if r["date"]), default=None)}
        return self._data

    def _local_day(self, as_of: datetime) -> str:
        return as_of.astimezone(ZoneInfo(self.s.local_tz)).date().isoformat()

    def _meta(self, day: str) -> list[dict]:
        out = []
        for c in self.contracts.all():
            vs = [v for v in self.versions.for_contract(c["contract_id"]) if v["effective_from"] < day]
            if not vs:
                continue
            device = self.devices.get(c["device_id"]) or {}
            site = self.sites.get(c["site_id"]) or {}
            out.append({"contract": c, "version": vs[-1], "device": device, "region_code": site.get("region_code"),
                        "customer_id": c.get("customer_id"), "material_stream": c["material_stream"],
                        "pricing_model": vs[-1]["pricing_model"], "bucket": bucket(device.get("container_volume_m3")),
                        "operator_id": c["operator_id"]})
        return out

    @staticmethod
    def _reprice(events: list[dict], version: dict) -> int:
        return sum(ln["amount_cents"] for e in events
                   for ln in price_event(version, e["pickup_status"], e["weight_kg"], **e["price_args"]))

    def _over_rates(self, as_of: datetime) -> dict[str, float]:
        d = self._load()
        billed, over, delta = {}, {}, {}
        for inv in d["invoices"].values():
            if ts(inv["issued_at"]) and ts(inv["issued_at"]) <= as_of and inv.get("operator_id"):
                billed[inv["operator_id"]] = billed.get(inv["operator_id"], 0) + (inv["total_cents"] or 0)
        for it in d["items"]:
            inv = d["invoices"].get(it.get("invoice_id") or "")
            if not inv or not ts(inv["issued_at"]) or ts(inv["issued_at"]) > as_of:
                continue
            op = inv["operator_id"]
            delta[op] = delta.get(op, 0) + it["euros_at_stake_cents"]
            over[op] = over.get(op, 0) + max(0, it["euros_at_stake_cents"])
        return {op: over.get(op, 0) / (b - delta.get(op, 0)) for op, b in billed.items() if b - delta.get(op, 0) > 0}

    def value(self, contract_id: str, as_of: datetime, candidates: tuple[str, ...] = ACTIONS) -> dict:
        d, s = self._load(), self.s
        day = self._local_day(as_of)
        meta = self._meta(day)
        me = next((m for m in meta if m["contract"]["contract_id"] == contract_id), None)
        if not me:
            return {"contract_id": contract_id, "values": {}, "chosen": [], "annual_cost_cents": None}
        events = [r for r in d["rows"] if r["contract_id"] == contract_id and r["date"] and r["date"] < day
                  and r["price_args"] is not None]
        lifts = [r for r in events if r["pickup_status"] in LIFT_STATUSES]
        cred = bool((self.materials.get(me["material_stream"]) or {}).get("credit_eligible"))
        start = max(me["device"].get("active_from") or d["start"] or day, d["start"] or day)
        days = max(30.0, (datetime.fromisoformat(day) - datetime.fromisoformat(start)).days)
        ann, months_active = 365.0 / days, days / 30.4375
        own = me["version"]
        rental = lambda v: round(int(v["rental_cents_per_month"] or 0) * months_active)
        base = self._reprice(events, own) + rental(own)
        values: dict[str, dict] = {}

        published = {r["pickup_id"] for r in lifts if self._published(r, as_of)}
        has_weight = bool(me["device"].get("has_weight_measurement"))
        recoverable = 0
        for it in d["items"]:
            inv = d["invoices"].get(it.get("invoice_id") or "")
            if it.get("contract_id") != contract_id or not inv or it.get("family") not in RECOVERABLE:
                continue
            issued = ts(inv["issued_at"])
            if not issued or not (as_of - timedelta(days=s.dispute_lookback_days) < issued <= as_of):
                continue
            if inv.get("dispute_status") in ("RESOLVED_CREDIT_NOTE", "OPEN") or it["euros_at_stake_cents"] <= 0:
                continue
            if it["family"] == "WEIGHT_BASIS_MISMATCH" and not (has_weight or it.get("pickup_id") in published):
                continue
            recoverable += it["euros_at_stake_cents"]
        if "DISPUTE_INVOICE" in candidates:
            values["DISPUTE_INVOICE"] = {"value_cents": round(s.dispute_recovery_rate * recoverable - s.dispute_admin_cost_cents),
                                         "recoverable_cents": recoverable}

        share = len(published) / len(lifts) if lifts else 0.0
        if "REQUEST_WEIGHBRIDGE_DATA" in candidates and share < 0.8:
            rate_t = int(own["haul_fee_cents_per_t"] or 0) + int(own["processing_fee_cents_per_t"] or 0)
            gap_kg = sum(r["ticket_kg"] - r["device_kg"] for r in lifts
                         if r["ticket_kg"] is not None and r["device_kg"] is not None and r["pickup_id"] in published)
            tare_over = max(0.0, gap_kg) / 1000 * rate_t
            unverified = 0.0
            if not has_weight:
                rate = self._weight_basis_rate(me["operator_id"], as_of)
                unverified = rate * sum((ln["operator"] or {}).get("amount_cents") or 0 for r in lifts
                                        if r["pickup_id"] not in published for ln in r["lines"]
                                        if ln["line_type"] in ("HAUL_PER_TONNE", "PROCESSING"))
            values["REQUEST_WEIGHBRIDGE_DATA"] = {
                "value_cents": round(s.request_comply_prob * (tare_over + unverified) * ann - s.request_admin_cost_cents),
                "share_with_ticket": round(share, 3)}

        target = {k: me[k] for k in ("region_code", "material_stream", "pricing_model", "bucket")}
        if "RENEGOTIATE_CONTRACT" in candidates:
            peer, level = peer_terms(meta, target)
            if peer:
                nv = self._terms(own, peer, cred, FEE_FIELDS)
                reneg = self._reprice(events, nv) + rental(nv)
                gap = base - reneg
                ok = base > 0 and gap >= s.renegotiation_min_gap_pct / 100 * base
                values["RENEGOTIATE_CONTRACT"] = {
                    "value_cents": round((s.renegotiation_success_prob * gap * ann if ok else 0) - s.renegotiation_effort_cents),
                    "annual_gap_cents": round(gap * ann), "peer_level": level}
        if "TENDER_OR_SWITCH_OPERATOR" in candidates:
            rates = self._over_rates(as_of)
            months_benefit = max(0.0, s.valuation_horizon_months - int(me["contract"]["notice_period_days"] or 0) / 30.4375)
            best = None
            for op in self.operators.all():
                if op["operator_id"] == me["operator_id"] or me["region_code"] not in str(op.get("regions_served") or "").split(","):
                    continue
                pv, _ = peer_terms([m for m in meta if m["operator_id"] == op["operator_id"]], target, min_n=2)
                if not pv:
                    continue
                av = self._terms(own, pv, cred, FEE_FIELDS + ["free_km"])
                alt = self._reprice(events, av) + rental(av)
                cur_tot = base * (1 + rates.get(me["operator_id"], 0.0))
                alt_tot = alt * (1 + rates.get(op["operator_id"], 0.0))
                gap = cur_tot - alt_tot
                ok = cur_tot > 0 and gap >= s.tender_min_gap_pct / 100 * cur_tot
                v = (s.tender_success_prob * gap * ann * months_benefit / 12 if ok else 0) - s.tender_switch_cost_cents
                if best is None or v > best["value_cents"]:
                    best = {"value_cents": round(v), "alternative": op["operator_id"]}
            if best:
                values["TENDER_OR_SWITCH_OPERATOR"] = best
        return {"contract_id": contract_id, "operator_id": me["operator_id"], "values": values,
                "chosen": self.choose(values), "annual_cost_cents": round(base * ann)}

    @staticmethod
    def choose(values: dict) -> list[str]:
        chosen = [a for a in ("DISPUTE_INVOICE", "REQUEST_WEIGHBRIDGE_DATA") if values.get(a, {}).get("value_cents", 0) > 0]
        excl = [(values[a]["value_cents"], a) for a in ("RENEGOTIATE_CONTRACT", "TENDER_OR_SWITCH_OPERATOR")
                if a in values and values[a]["value_cents"] > 0]
        return chosen + ([max(excl)[1]] if excl else [])

    @staticmethod
    def _terms(own: dict, peer: dict, cred: bool, fields: list[str]) -> dict:
        v = dict(own)
        for f in fields:
            v[f] = int(round(peer[f]))
        v["credit_share_bp"] = int(round(peer["credit_share_bp"] / 100) * 100) if cred else 0
        return v

    def _published(self, row: dict, as_of: datetime) -> bool:
        t = self._load()["tickets"].get(row["operator_job_ref"] or "")
        return bool(t) and ts(t.get("published_at")) is not None and ts(t["published_at"]) <= as_of

    def _weight_basis_rate(self, operator_id: str, as_of: datetime) -> float:
        d = self._load()
        over = sum(max(0, it["euros_at_stake_cents"]) for it in d["items"]
                   if it.get("operator_id") == operator_id and it.get("family") == "WEIGHT_BASIS_MISMATCH")
        base = sum((ln["operator"] or {}).get("amount_cents") or 0 for r in d["rows"]
                   if r["operator_id"] == operator_id and r["ticket_kg"] is not None and self._published(r, as_of)
                   for ln in r["lines"] if ln["line_type"] in ("HAUL_PER_TONNE", "PROCESSING"))
        return over / base if base > 0 else 0.0

    def cases(self, cases: list[dict]) -> list[dict]:
        out = []
        for c in cases:
            cand = tuple(a for a in str(c["candidate_actions"]).split(",") if a)
            v = self.value(c["contract_id"], ts(c["as_of_at"]), cand)
            out.append({"case_id": c["case_id"], "actions": ";".join(a for a in v["chosen"] if a in cand),
                        "values": v["values"]})
        return out

    def now(self) -> datetime:
        d = self._load()
        issued = [ts(i["issued_at"]) for i in d["invoices"].values() if i.get("issued_at")]
        return max(issued) if issued else datetime.now(timezone.utc)
