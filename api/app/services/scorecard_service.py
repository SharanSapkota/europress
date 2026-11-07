from statistics import median
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.services.comparison_service import ComparisonService
from app.services.cost_service import material_name, recent_rows
from app.services.explain import listing, why
from app.services.periods import resolve
from app.services.operator_action_service import OperatorActionService, ts
from app.services.pricing import LIFT_STATUSES
from app.services.suggestion_service import MEASURES, SuggestionService

OPERATOR_STATUSES = ("COMPLETED", "PARTIAL", "MISSED_BY_OPERATOR", "WASTED_TRIP")
EXPORT_WINDOW_HOURS = 2


def rate(n: int, d: int) -> float | None:
    return n / d if d else None


class ScorecardService:
    def __init__(self, comparison: ComparisonService, actions: OperatorActionService, suggestions: SuggestionService,
                 pickups, tickets, devices, sites, contracts, operators, decisions, settings: Settings):
        self.comparison = comparison
        self.actions = actions
        self.suggestions = suggestions
        self.pickups = pickups
        self.tickets = tickets
        self.devices = devices
        self.sites = sites
        self.contracts = contracts
        self.operator_repo = operators
        self.decisions = decisions
        self.s = settings
        self.tz = ZoneInfo(settings.local_tz)

    def _month(self, text: str | None) -> str | None:
        t = ts(text)
        return t.astimezone(self.tz).strftime("%Y-%m") if t else None

    def job(self, p: dict, ticket: dict | None, device: dict | None, region: str | None, window_hours: float) -> dict:
        act, sched, order = ts(p.get("actual_at")), ts(p.get("scheduled_at")), ts(p.get("order_placed_at"))
        lift = p["status"] in LIFT_STATUSES
        t = ticket if lift else None
        lag = None
        if t and t.get("published_at") and t.get("arrival_at"):
            lag = (ts(t["published_at"]) - ts(t["arrival_at"])).total_seconds() / 86400
        est = p.get("device_estimated_collected_kg")
        weighed = round(est) if device and device.get("has_weight_measurement") and est is not None and est > 0 else None
        return {
            "key": (p["operator_id"], region, self._month(p.get("scheduled_at"))), "status": p["status"], "lift": lift,
            "on_time": bool(lift and act and sched and abs((act - sched).total_seconds()) <= window_hours * 3600),
            "order_h": (act - order).total_seconds() / 3600 if lift and act and order else None,
            "ticket": t is not None and t.get("published_at") is not None, "lag": lag,
            "ticket_id": (t or {}).get("ticket_id"), "pickup_id": p.get("collection_id"), "device_id": p.get("device_id"),
            "alloc": t.get("allocated_net_kg") if t else None, "loads": (t or {}).get("loads_on_vehicle") or 1,
            "dev": est if est is not None and est > 50 else None, "weighed": weighed,
        }

    def _facts(self, customer_id: str | None, months: int | list[str], window_hours: float,
               site_id: str | None = None) -> dict:
        periods, rows, results = recent_rows(self.comparison, months, customer_id, customer_id is None)
        if site_id:
            rows = [r for r in rows if r["site_id"] == site_id]
        region = {s["site_id"]: s.get("region_code") for s in self.sites.all()}
        contract_site = {c["contract_id"]: c.get("site_id") for c in self.contracts.all()}
        tickets = {t["operator_job_ref"]: t for t in self.tickets.all() if t.get("operator_job_ref")}
        jobs = []
        for p in self.pickups.all():
            if p["status"] not in OPERATOR_STATUSES or (customer_id and p.get("customer_id") != customer_id) \
                    or (site_id and p.get("site_id") != site_id):
                continue
            j = self.job(p, tickets.get(p.get("operator_job_ref") or ""), self.devices.get(p["device_id"]),
                         region.get(p["site_id"]), window_hours)
            if j["key"][2] in periods:
                jobs.append(j)
        lines, missing = [], []
        appearances = [dict(r, period=res["period"]) for res in results for r in res["rows"]
                       if not site_id or r["site_id"] == site_id]
        invoiced = {r["pickup_id"] for r in appearances if r["invoice_ids"]}
        for r in appearances:
            key = (r["operator_id"], region.get(r["site_id"]), r["period"])
            flagged = {i["entity_id"] for i in r["items"] if i["status"] == "CHECK" and i["entity_type"] == "invoice_line"}
            open_row = r["status"] == "CHECK"
            for lr in r["lines"]:
                if lr["line_type"] == "RENTAL":
                    continue
                if lr["operator"]:
                    exp = 0 if lr["duplicate"] or not lr["ours"] else lr["ours"]["amount_cents"]
                    check = open_row and lr["invoice_line_id"] in flagged
                    lines.append({"key": key, "exp": exp, "diff": lr["operator"]["amount_cents"] - exp, "check": check,
                                  "strong": check and r["suggested_action"] == "CORRECT_LINE"})
                elif lr["ours"] and r["invoice_ids"]:
                    missing.append({"key": key, "cents": lr["ours"]["amount_cents"]})
        for r in rows:
            if r["pickup_id"] not in invoiced and r["pickup_status"] in LIFT_STATUSES and r["ours"]["amount_cents"]:
                missing.append({"key": (r["operator_id"], region.get(r["site_id"]), r["period"]),
                                "cents": r["ours"]["amount_cents"]})
        for res in results:
            invs = {i["invoice_id"]: i for i in res["invoices"]}
            for u in res["unmatched_lines"]:
                inv = invs.get(u["invoice_id"], {})
                if site_id and contract_site.get(inv.get("contract_id")) != site_id:
                    continue
                check = u["status"] == "CHECK"
                lines.append({"key": (inv.get("operator_id"), region.get(contract_site.get(inv.get("contract_id"))),
                                      res["period"]), "exp": 0, "diff": u["euros_at_stake_cents"], "check": check,
                              "strong": check})
        return {"periods": periods, "jobs": jobs, "lines": lines, "missing": missing}

    @staticmethod
    def metrics(jobs: list[dict], lines: list[dict], missing: list[dict]) -> dict:
        lifts = [j for j in jobs if j["lift"]]
        lags = [j["lag"] for j in lifts if j["lag"] is not None]
        orders = [j["order_h"] for j in lifts if j["order_h"] is not None]
        both = [j for j in lifts if j["alloc"] is not None and j["dev"] is not None]
        dev_sum = sum(j["dev"] for j in both)
        single = [100 * (j["alloc"] - j["weighed"]) / j["weighed"] for j in lifts
                  if j["alloc"] is not None and j["weighed"] and j["loads"] == 1]
        expected = sum(ln["exp"] for ln in lines) + sum(m["cents"] for m in missing)
        over = sum(ln["diff"] for ln in lines if ln["diff"] > 0)
        under = -sum(ln["diff"] for ln in lines if ln["diff"] < 0) + sum(m["cents"] for m in missing)
        missed = sum(j["status"] == "MISSED_BY_OPERATOR" for j in jobs)
        return {
            "n_operator_jobs": len(jobs), "n_completed_lifts": len(lifts),
            "on_time_rate": rate(sum(j["on_time"] for j in lifts), len(lifts)),
            "missed_visits": missed, "missed_visit_rate": rate(missed, len(jobs)),
            "tickets_shared_rate": rate(sum(j["ticket"] for j in lifts), len(lifts)),
            "weighbridge_shared_7d_rate": rate(sum(j["ticket"] and (j["lag"] or 0) <= 7 for j in lifts), len(lifts)),
            "median_share_lag_days": median(lags) if lags else None,
            "billing_overcharge_pct": 100 * over / expected if abs(expected) > 100 else None,
            "billing_undercharge_pct": 100 * under / expected if abs(expected) > 100 else None,
            "discrepant_line_rate": rate(sum(ln["diff"] != 0 for ln in lines) + len(missing), len(lines) + len(missing)),
            "lines_to_check": sum(ln["check"] for ln in lines), "strong_lines": sum(ln["strong"] for ln in lines),
            "invoice_lines": len(lines),
            "weight_bias_pct": 100 * (sum(j["alloc"] for j in both) - dev_sum) / dev_sum if dev_sum else None,
            "weight_gap_median_pct": median(single) if single else None, "weight_pairs": len(single),
            "median_order_to_lift_hours": median(orders) if orders else None,
        }

    def scorecard_rows(self, months: int = 0) -> list[dict]:
        f = self._facts(None, months, EXPORT_WINDOW_HOURS)
        keys = sorted({j["key"] for j in f["jobs"]} | {ln["key"] for ln in f["lines"]}, key=lambda k: tuple(map(str, k)))
        return [{"operator_id": k[0], "region_code": k[1], "month": k[2],
                 **self.metrics([j for j in f["jobs"] if j["key"] == k], [ln for ln in f["lines"] if ln["key"] == k],
                                [x for x in f["missing"] if x["key"] == k])}
                for k in keys if k[0] and k[1]]

    def flags(self, m: dict) -> dict[str, str]:
        s = self.s
        good = {
            "on_time": m["on_time_rate"] is None or m["on_time_rate"] >= s.on_time_min,
            "missed_visits": m["missed_visits"] <= s.missed_visits_max,
            "tickets_shared": m["tickets_shared_rate"] is None or (m["tickets_shared_rate"] >= s.tickets_shared_min and
                                                                   (m["median_share_lag_days"] or 0) <= s.share_lag_max_days),
            "lines_to_check": not m["invoice_lines"] or m["lines_to_check"] / m["invoice_lines"] <= s.lines_check_max,
            "weight_vs_ours": m["weight_gap_median_pct"] is None or abs(m["weight_gap_median_pct"]) <= s.weight_gap_max_pct,
        }
        return {k: "GOOD" if v else "CHECK" for k, v in good.items()}

    def operators(self, customer_id: str | None = None, site_id: str | None = None, period: str | None = "all",
                  start: str | None = None, end: str | None = None, operator_id: str | None = None) -> dict:
        everyone = customer_id == "all"
        cid = None if everyone else self.comparison.customer_id(customer_id)
        available = self.comparison.data_months()
        chosen = resolve(available, period, start, end)
        f = self._facts(cid, chosen, self.s.on_time_window_hours, site_id) if chosen else \
            {"periods": [], "jobs": [], "lines": [], "missing": []}
        op_ids = sorted({j["key"][0] for j in f["jobs"]} | {ln["key"][0] for ln in f["lines"] if ln["key"][0]})
        op_ids = [o for o in op_ids if not operator_id or o == operator_id]
        decided = self.decisions.current("operator", op_ids)
        names = self.comparison.names([], [], cid)
        return {"customer_id": "all" if everyone else cid,
                "customer_name": "All customers" if everyone else names["customer_name"],
                "filters": {"customer_id": "all" if everyone else cid, "site_id": site_id, "period": period or "all",
                            "from": start, "to": end, "operator_id": operator_id},
                "options": self._options(cid, available),
                "months": len(f["periods"]), "periods": f["periods"],
                "on_time_window_hours": self.s.on_time_window_hours,
                "operators": [self._card(op, f, decided.get(op) or {}, cid, site_id) for op in op_ids]}

    def _options(self, cid: str | None, months: list[str]) -> dict:
        customers = self.comparison.customers.all() if self.comparison.customers else []
        sites = [s for s in self.sites.all() if not cid or s.get("customer_id") == cid]
        return {"customers": [{"id": c["customer_id"], "name": c.get("customer_name") or c["customer_id"]} for c in customers],
                "sites": [{"id": s["site_id"], "name": s.get("site_name") or s["site_id"]} for s in sites],
                "operators": [{"id": o["operator_id"], "name": o.get("operator_name") or o["operator_id"]}
                              for o in self.operator_repo.all()],
                "months": months}

    def _card(self, op: str, f: dict, decision: dict, cid: str | None, site_id: str | None = None) -> dict:
        def pick(items, month=None):
            return [x for x in items if x["key"][0] == op and (month is None or x["key"][2] == month)]

        m = self.metrics(pick(f["jobs"]), pick(f["lines"]), pick(f["missing"]))
        flags = self.flags(m)
        monthly = [self.flags(self.metrics(pick(f["jobs"], p), pick(f["lines"], p), pick(f["missing"], p)))
                   for p in f["periods"]]
        recent = monthly[-self.s.pattern_months:]
        persistent = [k for k in MEASURES if len(recent) >= self.s.pattern_months and all(x[k] == "CHECK" for x in recent)]
        contracts = [c for c in self.contracts.all() if c["operator_id"] == op and (not cid or c.get("customer_id") == cid)
                     and (not site_id or c.get("site_id") == site_id)]
        covered = sorted({x["key"][2] for x in pick(f["jobs"]) + pick(f["lines"]) if x["key"][2]})
        name = (self.operator_repo.get(op) or {}).get("operator_name") or op
        declined = self.decisions.declined("operator", op, "RENEGOTIATE")
        values = self._values(contracts) if persistent else {}
        tip = self.suggestions.suggest(flags, persistent, declined, values, m)
        latest = decision if (decision.get("suggestion") or {}).get("action") == tip["action"] else {}
        draft = self.suggestions.draft(tip["action"], name, m)
        return {
            "operator_id": op, "name": name,
            "materials": sorted({material_name(c["material_stream"]) for c in contracts}),
            "pickups": m["n_completed_lifts"], "months": len(covered), "months_covered": covered,
            "enough_data": m["n_completed_lifts"] >= self.s.sure_min_pickups,
            "measures": self._measures(m, flags, pick(f["jobs"]), contracts),
            "status": "CHECK" if "CHECK" in flags.values() else "GOOD",
            "persistent_checks": persistent, "suggested_action": tip["action"], "suggestion": tip["title"],
            "why": tip["why"], "value_cents": tip["value_cents"], "value_is_estimate": True,
            "decision": latest.get("decision"), "decided_at": latest.get("created_at"),
            "decision_id": latest.get("decision_id"),
            "suggestion_why": why(tip["title"], listing([c["contract_id"] for c in contracts], "Contracts") +
                                  "; the five measures above", "high" if tip["action"] == "NONE" else "low",
                                  tip["why"] if not tip["value_cents"] else
                                  f"{tip['why']} The expected value uses the published valuation rules "
                                  f"(ECONOMIC_MODEL section 7) and is not proof of a real saving.",
                                  "hypothetical" if tip["value_cents"] else "estimated"),
            "draft": draft if latest.get("decision") == "prepare" else None, "_draft": draft,
        }

    def _values(self, contracts: list[dict]) -> dict[str, int]:
        as_of = self.actions.now()
        total: dict[str, int] = {}
        for c in contracts:
            for a, v in self.actions.value(c["contract_id"], as_of)["values"].items():
                total[a] = total.get(a, 0) + v["value_cents"]
        return total

    def _measures(self, m: dict, flags: dict, jobs: list[dict], contracts: list[dict]) -> list[dict]:
        rows = self._measure_rows(m, flags)
        lifts = [j for j in jobs if j["lift"]]
        facts = self.suggestions.facts(m)
        tickets = listing([j["ticket_id"] for j in lifts if j["ticket_id"]], "Scale tickets")
        pickups = listing([j["pickup_id"] for j in jobs], "Pickups")
        devices = listing([j["device_id"] for j in lifts if j["weighed"]], "Device estimates")
        lines = listing([c["contract_id"] for c in contracts], "Invoice lines of contracts")
        count = {"on_time": len(lifts), "missed_visits": len(jobs), "tickets_shared": len(lifts),
                 "lines_to_check": m["invoice_lines"], "weight_vs_ours": m["weight_pairs"]}
        src = {"on_time": pickups, "missed_visits": pickups, "tickets_shared": f"{tickets or 'No scale tickets'}; {pickups}",
               "lines_to_check": lines, "weight_vs_ours": f"{tickets or 'No scale tickets'}; {devices or 'no device weights'}"}
        for r in rows:
            n = count[r["key"]]
            conf = "not enough data" if not n else ("high" if n >= self.s.sure_min_pickups else "low")
            reason = f"{facts[r['key']][0].upper()}{facts[r['key']][1:]}." if r["status"] == "CHECK" else None
            if r["key"] == "weight_vs_ours":
                note = ("A gap can come from the device (sensor drift), the weighbridge (stored tare) or a shared "
                        "truck, not only from the operator.")
                reason = f"{reason} {note}" if reason else note
            r["why"] = why(r["source"], src[r["key"]] or None, conf, reason,
                           "estimated" if r["key"] in ("lines_to_check", "weight_vs_ours") else "observed")
        return rows

    def _measure_rows(self, m: dict, flags: dict) -> list[dict]:
        window = f"{self.s.on_time_window_hours:g} hours"
        shared = "No pickups"
        if m["tickets_shared_rate"] is not None:
            lag = m["median_share_lag_days"]
            shared = f"{round(m['tickets_shared_rate'] * 100)}%" + (f", after {lag:.0f} days" if lag is not None else "")
        gap = m["weight_gap_median_pct"]
        return [
            {"key": "on_time", "label": "On time", "status": flags["on_time"],
             "value": f"{round(m['on_time_rate'] * 100)}% of pickups" if m["on_time_rate"] is not None else "No pickups",
             "source": f"Your pickup records: {m['n_completed_lifts']} pickups, done within {window} of the planned time."},
            {"key": "missed_visits", "label": "Missed visits", "value": str(m["missed_visits"]), "status": flags["missed_visits"],
             "source": f"Your pickup records: {m['n_operator_jobs']} planned visits. Low-fill skips and your own "
                       f"cancellations are not counted."},
            {"key": "tickets_shared", "label": "Scale tickets shared", "value": shared, "status": flags["tickets_shared"],
             "source": "Published weighbridge tickets per pickup; the delay is the median from weighing to sharing."},
            {"key": "lines_to_check", "label": "Invoice lines to check", "status": flags["lines_to_check"],
             "value": f"{m['lines_to_check']} of {m['invoice_lines']}",
             "source": "Invoice lines that differ from your contract (Invoices page)."},
            {"key": "weight_vs_ours", "label": "Weight vs ours", "status": flags["weight_vs_ours"],
             "value": f"{gap:+.0f}%" if gap is not None else "Not enough data",
             "source": f"Median difference between the scale ticket and your device weight, {m['weight_pairs']} "
                       f"single-load pickups."},
        ]

    def decide(self, operator_id: str, decision: str, **filters) -> dict | None:
        card = next((c for c in self.operators(**filters, operator_id=operator_id)["operators"]), None)
        if not card or card["suggested_action"] == "NONE":
            return None
        saved = self.decisions.record("operator", operator_id, decision, card["name"],
                                      {"action": card["suggested_action"], "text": f"{card['suggestion']} {card['why']}"},
                                      {m["key"]: m["value"] for m in card["measures"]})
        return {**saved, "operator_id": operator_id, "action": card["suggested_action"],
                "draft": card["_draft"] if decision == "prepare" else None}
