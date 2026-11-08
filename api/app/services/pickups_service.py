from collections import defaultdict
from datetime import timedelta
from statistics import median

from app.core.config import Settings
from app.services.cards import advanced, bar, card, days, details, eur, evidence, example, fig, finish, kg, row, tonnes
from app.services.feature_data import FeatureData, FeatureDecisions, ts
from app.services.pricing import LIFT_STATUSES, credit_price_cents_per_t, rhu

VISIT_LINES = ("LIFT_FEE", "TRANSPORT", "REMOTE_SURCHARGE", "FUEL_SURCHARGE")


class PickupsService:
    def __init__(self, data: FeatureData, decisions, settings: Settings):
        self.data = data
        self.decisions = FeatureDecisions(decisions)
        self.s = settings

    def min_charge(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        topups, could_wait = [], []
        for did, ps in FeatureData.lifts_by_device(d).items():
            dev = d["devices"].get(did) or {}
            max_days = int((d["materials"].get(dev.get("material_stream")) or {}).get("max_days_between_collections") or 28)
            for prev, p in zip([None] + ps[:-1], ps):
                r = d["rows"].get(p["collection_id"])
                if not r or not r["version"] or not any(ln["line_type"] == "MIN_CHARGE_TOPUP" for ln in r["our_lines"]):
                    continue
                v = r["version"]
                fixed = sum(ln["amount_cents"] for ln in r["our_lines"] if ln["line_type"] in VISIT_LINES)
                per_t = int(v["haul_fee_cents_per_t"] or 0) + int(v["processing_fee_cents_per_t"] or 0)
                mass = r.get("device_kg") or r.get("weight_kg")
                breakeven = (int(v["min_charge_cents"]) - fixed) * 1000 / per_t if per_t else None
                topup = sum(ln["amount_cents"] for ln in r["our_lines"] if ln["line_type"] == "MIN_CHARGE_TOPUP")
                item = {"pickup_id": p["collection_id"], "device_id": did, "site": FeatureData.site_name(d, did),
                        "date": r["date"], "mass_kg": mass, "breakeven_kg": breakeven, "topup_cents": topup,
                        "max_days": max_days, "could_wait": False, "extra_days": None, "gap_days": None,
                        "blocked": "No earlier pickup to compare"}
                topups.append(item)
                if not (prev and mass and breakeven and mass > 0):
                    continue
                gap_days = max(1.0, (ts(p["actual_at"]) - ts(prev["actual_at"])).total_seconds() / 86400)
                extra = (breakeven - mass) / (mass / gap_days)
                target = (ts(p["actual_at"]) + timedelta(days=extra)).date().isoformat()
                open_day = (d["calendar"].get((p["site_id"], target)) or {}).get("is_open", True)
                if gap_days + extra <= max_days and open_day:
                    item.update(could_wait=True, extra_days=extra, gap_days=gap_days, blocked=None)
                    could_wait.append(item)
                else:
                    item["blocked"] = ("Hygiene limit, had to go" if gap_days + extra > max_days
                                       else "Site closed next, had to go")
        best = max(could_wait, key=lambda c: c["topup_cents"], default=None)
        total = sum(t["topup_cents"] for t in topups)
        status = "Check this" if could_wait else ("Good" if topups else "Not enough data")
        ex = None
        if best:
            ex = example(best["site"], best["device_id"], [
                fig("Pickup", best["pickup_id"], tag="OBSERVED"),
                fig("Weight at pickup", round(best["mass_kg"]), "kg", "ESTIMATED", "± 3.3 %"),
                fig("Break-even weight", round(best["breakeven_kg"]), "kg", "ESTIMATED"),
                fig("Minimum charge top-up", round(best["topup_cents"] / 100, 2), "€", "OBSERVED"),
                fig("More days it could wait", round(best["extra_days"], 1), "days", "ESTIMATED"),
                fig("Days allowed between pickups", best["max_days"], "days", "OBSERVED"),
            ], [bar("Break-even weight", best["breakeven_kg"], "kg", "ESTIMATED"),
                bar("Weight at pickup", best["mass_kg"], "kg", "ESTIMATED")],
                f"Waiting about {best['extra_days']:.1f} more days would have avoided a {eur(best['topup_cents'])} "
                f"minimum charge top-up and stayed within the {best['max_days']}-day limit.")
        c = card(
            "pickups.min_charge_guard", "Minimum charge guard", "Protects you from paying for air on light pickups.",
            status,
            "Some pickups are so light that the contract adds a minimum charge top-up. The container weight shows "
            "how far each load was from the weight where the top-up disappears. Where the site was open and the "
            "material could wait, a later pickup would have cost less.",
            ("A fill reading can look full while the load is still light, so a pickup is ordered too early.",
             f"{len(topups)} pickups had a minimum charge top-up, {eur(total)} in {d['months']} months; "
             f"{len(could_wait)} could have waited.",
             "Order pickups by weight near the break-even point, within the days allowed and when the site is open."),
            ex,
            evidence("ESTIMATED", "weights ± 3.3 %", len(topups),
                     "Container weight before each pickup, your contract's fees and minimum charge, the days allowed "
                     "between pickups for the material, and the site opening calendar.",
                     "This is about light loads that trigger a minimum charge, not about pickups that were not needed "
                     "at all. The top-up follows your contract terms."),
            advanced("break-even kg = (minimum charge − lift, transport, remote and fuel fees) × 1000 / (haul + "
                     "processing per tonne); more days = (break-even − weight) / (weight / days since the last pickup)",
                     ["Pickup", "Site", "Date", "Weight kg", "Break-even kg", "Top-up €", "Could wait", "More days"],
                     [[t["pickup_id"], t["site"], t["date"], round(t["mass_kg"] or 0), round(t["breakeven_kg"] or 0),
                       round(t["topup_cents"] / 100, 2), "Yes" if t["could_wait"] else "No",
                       round(t["extra_days"], 1) if t["extra_days"] is not None else None]
                      for t in sorted(topups, key=lambda t: -t["topup_cents"])]))
        wait_cents = sum(t["topup_cents"] for t in could_wait)
        ordered = sorted(topups, key=lambda t: (not t["could_wait"], -t["topup_cents"]))
        c["details"] = details(
            f"{len(topups)} top-ups · {eur(total)} in {d['months']} months · {len(could_wait)} could have waited",
            "Break-even = the weight where the minimum charge stops adding a top-up. Days to wait = how long until "
            "the container reaches it at its usual rate. Weights ± 3.3 %.",
            ["Date", "Container", "Load", "Top-up"],
            [row(t["date"], FeatureData.container(d, t["device_id"]), t["topup_cents"] / 100, "€",
                 t["mass_kg"], t["breakeven_kg"], f"{tonnes(t['mass_kg'])} / {tonnes(t['breakeven_kg'])} t",
                 f"Could wait {days(t['extra_days'])}" if t["could_wait"] else t["blocked"],
                 "check" if t["could_wait"] else "muted") for t in ordered])
        finish(c, f"{len(could_wait)} light pickups could have waited and saved {eur(wait_cents)} in top-ups",
               f"{best['pickup_id']}: {kg(best['mass_kg'])} at pickup · break-even {kg(best['breakeven_kg'])} · "
               f"top-up {eur(best['topup_cents'])}" if best else "", wait_cents)
        return {"card": c, "topups": topups, "could_wait": could_wait, "months": d["months"]}

    def _grades(self, d: dict) -> dict[str, list[tuple[str, str]]]:
        ticket_device = {}
        for t in d["tickets"]:
            p = d["by_job"].get(t.get("operator_job_ref"))
            if p:
                ticket_device[t["ticket_id"]] = p["device_id"]
        out: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for q in sorted(d["quality"], key=lambda q: (q.get("assessed_at") or "", q["ticket_id"])):
            if ticket_device.get(q["ticket_id"]):
                out[ticket_device[q["ticket_id"]]].append((q.get("assessed_at") or "", q["grade"]))
        return out

    def day0(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        tickets = {t["operator_job_ref"]: t for t in d["tickets"] if t.get("operator_job_ref")}
        grades = self._grades(d)
        items = []
        for p in d["pickups"]:
            r = d["rows"].get(p["collection_id"])
            dev = d["devices"].get(p["device_id"]) or {}
            mat = d["materials"].get(dev.get("material_stream")) or {}
            if not r or not mat.get("credit_eligible") or p["status"] not in LIFT_STATUSES or not r.get("device_kg"):
                continue
            idx = d["index"].get(((d["contracts"].get(p["contract_id"]) or {}).get("price_index_id"), (r["date"] or "")[:7]))
            if not idx or not r["version"]:
                continue
            index_cents = round(idx["price_eur_per_t"] * 100)
            prior = [g for at, g in grades[p["device_id"]] if at < (p.get("actual_at") or "")]
            grade = prior[-1] if prior else "B"
            expected = rhu(r["device_kg"] * credit_price_cents_per_t(r["version"], index_cents, grade), 1000)
            t = tickets.get(p.get("operator_job_ref"))
            delay = (ts(t["published_at"]) - ts(t["arrival_at"])).total_seconds() / 86400 if t and t.get("published_at") else None
            final = -sum(ln["amount_cents"] for ln in r["our_lines"] if ln["line_type"] == "MATERIAL_CREDIT")
            items.append({"pickup_id": p["collection_id"], "device_id": p["device_id"], "date": r["date"],
                          "site": FeatureData.site_name(d, p["device_id"]),
                          "operator_id": p.get("operator_id"), "kg": r["device_kg"], "grade": grade, "graded": bool(prior),
                          "expected_cents": expected, "delay_days": delay,
                          "final_cents": final if r["ours"]["weight_source"] == "ticket" else None})
        gaps = [abs(i["expected_cents"] - i["final_cents"]) / i["final_cents"] for i in items if i["final_cents"]]
        spread = median(gaps) if gaps else None
        for i in items:
            i["low_cents"] = round(i["expected_cents"] * (1 - spread)) if spread is not None else None
            i["high_cents"] = round(i["expected_cents"] * (1 + spread)) if spread is not None else None
        delays = [i["delay_days"] for i in items if i["delay_days"] is not None]
        slow = [i for i in items if i["delay_days"] is None or i["delay_days"] > self.s.share_lag_max_days]
        best = max((i for i in items if i["delay_days"] is not None), key=lambda i: i["delay_days"], default=None)
        ex = None
        if best:
            rng = f"{eur(best['low_cents'])}–{eur(best['high_cents'])}" if spread is not None else None
            ex = example(best["site"], best["device_id"], [
                fig("Pickup", best["pickup_id"], tag="OBSERVED"),
                fig("Weight at pickup", round(best["kg"]), "kg", "ESTIMATED", "± 3.3 %"),
                fig("Quality grade used", best["grade"] if best["graded"] else f"{best['grade']} (no grade yet)", tag="OBSERVED"
                    if best["graded"] else "ESTIMATED"),
                fig("Expected credit", round(best["expected_cents"] / 100), "€", "ESTIMATED", rng),
                fig("Scale ticket arrived after", round(best["delay_days"], 1), "days", "OBSERVED"),
                fig("Final credit", round(best["final_cents"] / 100) if best["final_cents"] else None, "€", "ESTIMATED"),
            ], [bar("Expected credit on the pickup day", best["expected_cents"] / 100, "€", "ESTIMATED"),
                bar("Credit once the ticket arrived", (best["final_cents"] or 0) / 100, "€", "ESTIMATED")],
                f"On the pickup day you would have seen an expected credit of {rng or eur(best['expected_cents'])}, "
                f"{best['delay_days']:.0f} days before the scale ticket arrived.")
        c = card(
            "pickups.day0_receipt", "Provisional pickup receipt",
            "Shows the weight and expected credit on the day of pickup.",
            "Worth a check" if slow else ("Good" if items else "Not enough data"),
            "For cardboard and plastics the credit depends on the weight and the quality grade. Some operators share "
            "the scale ticket days or weeks later. A provisional receipt on the pickup day shows the weight and an "
            "expected credit range, so you are not waiting in the dark.",
            ("Fill shows how full the container was, not how much material left the site.",
             f"{len(items)} pickups had a container weight on the day; the median scale ticket came after "
             f"{median(delays):.1f} days." if delays else f"{len(items)} pickups had a container weight on the day.",
             f"{len(slow)} pickups had a ticket after more than {self.s.share_lag_max_days:g} days or none; for them "
             f"the expected credit is known weeks earlier."),
            ex,
            evidence("ESTIMATED", f"credit ± {spread:.0%} (median gap to the final credit over {len(gaps)} pickups)"
                     if spread is not None else "weights ± 3.3 %", len(items),
                     "Container weight at pickup, your contract's credit share, the monthly price index and the "
                     "device's last known quality grade.",
                     "This is provisional. The final credit comes from the operator's scale ticket and quality grade."),
            advanced("expected credit = weight × index price × credit share × grade factor (last known grade, else B); "
                     "range = expected × (1 ± median gap to final credit)",
                     ["Pickup", "Site", "Weight kg", "Grade", "Expected €", "Range €", "Ticket after days", "Final €"],
                     [[i["pickup_id"], i["site"], round(i["kg"]), i["grade"] + ("" if i["graded"] else " (no grade yet)"),
                       round(i["expected_cents"] / 100),
                       f"{round(i['low_cents'] / 100)}–{round(i['high_cents'] / 100)}" if i["low_cents"] is not None else None,
                       round(i["delay_days"], 1) if i["delay_days"] is not None else None,
                       round(i["final_cents"] / 100) if i["final_cents"] else None]
                      for i in sorted(items, key=lambda i: -(i["delay_days"] or 999))]))
        lag = self.s.share_lag_max_days
        c["details"] = details(
            f"{len(items)} pickups · {len(slow)} without a ticket in {lag:g} days"
            + (f" · median {median(delays):.0f} days" if delays else ""),
            "Expected credit = weight × index price × credit share × quality factor, from the last known grade. "
            + (f"Range ± {spread:.0%}. " if spread is not None else "") + "Weights ± 3.3 %.",
            ["Date", "Container", "Expected credit", "Expected €"],
            [row(i["date"], FeatureData.container(d, i["device_id"]), i["expected_cents"] / 100, "€",
                 i["expected_cents"], max(i["expected_cents"], i["final_cents"] or 0),
                 f"{eur(i['low_cents'])}–{eur(i['high_cents'])}" if i["low_cents"] is not None else "",
                 "No scale ticket yet" if i["delay_days"] is None else f"Ticket after {days(i['delay_days'])}",
                 "check" if i["delay_days"] is None or i["delay_days"] > lag else "muted")
             for i in sorted(items, key=lambda i: -(i["delay_days"] if i["delay_days"] is not None else 1e9))])
        finish(c, f"{len(slow)} credit pickups had no scale ticket within {self.s.share_lag_max_days:g} days",
               f"{best['pickup_id']}: expected {eur(best['low_cents'])}–{eur(best['high_cents'])} on day 0 · ticket after "
               f"{best['delay_days']:.0f} days" if best and spread is not None else "",
               sum(i["expected_cents"] for i in slow))
        return {"card": c, "items": items, "spread": spread}

    def cards(self, customer_id: str | None = "all") -> dict:
        cards = [self.min_charge(customer_id)["card"], self.day0(customer_id)["card"]]
        return {"customer_id": customer_id or "all", "cards": self.decisions.apply(cards)}

    def decide(self, card_id: str, decision: str, customer_id: str | None = "all") -> dict | None:
        return self.decisions.record(self.cards(customer_id)["cards"], card_id, decision)
