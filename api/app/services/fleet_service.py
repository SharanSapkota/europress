from collections import defaultdict
from statistics import mean, median

from app.services.cards import advanced, bar, card, details, eur, evidence, example, fig, finish, kg, row, tonnes
from app.services.feature_data import FeatureData, FeatureDecisions, ts
from app.services.pricing import LIFT_STATUSES

SENSOR_WORK = ("SENSOR_RECALIBRATION", "SENSOR_REPLACEMENT")
LIMITS = {"COMBI": 22, "DUO": 30}
SIZES = (8, 10, 12, 16, 20, 22, 25, 30)
TARE_GAP_KG = 100
SERVICE_SHIFT_KG = 50
FULL_HOURS = 24
SIDE_WASTE_LIFTS = 2
MIN_USE = 0.6
LIFT_LINES = ("LIFT_FEE", "TRANSPORT", "REMOTE_SURCHARGE")


class FleetService:
    def __init__(self, data: FeatureData, decisions, params: dict):
        self.data = data
        self.decisions = FeatureDecisions(decisions)
        self.params = params

    def tare(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        tickets = d["tickets"] if not d["customer_id"] else [t for t in d["tickets"] if t.get("operator_job_ref") in d["by_job"]]
        by_vehicle = defaultdict(lambda: {"STORED": [], "WEIGHED": []})
        for t in tickets:
            if t.get("vehicle_id") and t.get("tare_kg") is not None and t.get("tare_method") in ("STORED", "WEIGHED"):
                by_vehicle[t["vehicle_id"]][t["tare_method"]].append(t)
        gaps = []
        for v, g in sorted(by_vehicle.items()):
            if g["STORED"] and g["WEIGHED"]:
                stored, weighed = mean(t["tare_kg"] for t in g["STORED"]), mean(t["tare_kg"] for t in g["WEIGHED"])
                last = max((t.get("arrival_at") or "" for t in g["STORED"] + g["WEIGHED"]), default=None)
                gaps.append({"vehicle_id": v, "last_at": last, "operator_id": g["STORED"][0].get("operator_id"), "stored": stored,
                             "weighed": weighed, "gap": stored - weighed, "stored_tickets": len(g["STORED"]),
                             "weighed_tickets": len(g["WEIGHED"])})
        big = [g for g in gaps if abs(g["gap"]) >= TARE_GAP_KG]
        serviced = self.serviced(d)
        best = max(gaps, key=lambda g: abs(g["gap"]), default=None)
        ex = None
        if best:
            ex = example(None, best["vehicle_id"], [
                fig("Truck", best["vehicle_id"], tag="OBSERVED"),
                fig("Stored empty weight (average)", round(best["stored"]), "kg", "OBSERVED"),
                fig("Weighed empty weight (average)", round(best["weighed"]), "kg", "OBSERVED"),
                fig("Difference", f"{best['gap']:+.0f}", "kg", "OBSERVED"),
                fig("Tickets with the stored weight", best["stored_tickets"], tag="OBSERVED"),
            ], [bar("Weighed empty weight", best["weighed"], "kg", "OBSERVED"),
                bar("Stored empty weight", best["stored"], "kg", "OBSERVED")],
                f"The stored empty weight of this truck is {abs(best['gap']):.0f} kg "
                f"{'above' if best['gap'] > 0 else 'below'} its weighed empty weight, on {best['stored_tickets']} tickets.")
        c = card(
            "fleet.tare", "Truck tare check", "Keeps the empty-truck weight on scale tickets up to date.",
            "Check this" if big else ("Good" if gaps else "Not enough data"),
            "A scale ticket is the full truck minus the empty truck. Some weighings use a stored empty weight instead "
            "of weighing the empty truck. Comparing both kinds of tickets for the same truck shows when the stored "
            "weight is out of date.",
            ("Fill readings cannot check a scale ticket at all.",
             f"{len(gaps)} trucks have both kinds of tickets; {len(big)} differ by {TARE_GAP_KG} kg or more.",
             "A data request to refresh the stored weight makes every later ticket more accurate."),
            ex,
            evidence("OBSERVED", None, sum(g["stored_tickets"] + g["weighed_tickets"] for g in gaps),
                     "Empty-truck weights on the operator's scale tickets, stored and weighed, per truck. Separately: "
                     f"our scale was serviced on {len(serviced)} containers, and their weight differences moved after "
                     "the service.",
                     "A stored weight can drift for normal reasons, such as new equipment on the truck. Asking for a "
                     "fresh weighing is a data request, not a complaint."),
            advanced("difference = average stored empty weight − average weighed empty weight, per truck",
                     ["Truck", "Operator", "Stored kg", "Weighed kg", "Difference kg", "Stored tickets", "Weighed tickets"],
                     [[g["vehicle_id"], g["operator_id"], round(g["stored"]), round(g["weighed"]), round(g["gap"]),
                       g["stored_tickets"], g["weighed_tickets"]] for g in sorted(gaps, key=lambda g: -abs(g["gap"]))] +
                     [["Our scale was serviced", s["device_id"], s["work"], s["date"], f"{s['before']:+.0f} → {s['after']:+.0f} kg",
                       None, None] for s in serviced]))
        c["details"] = details(
            f"{len(gaps)} trucks checked · {len(big)} off by {TARE_GAP_KG} kg or more · our scale serviced on "
            f"{len(serviced)} {'container' if len(serviced) == 1 else 'containers'}",
            "Difference = the stored empty-truck weight minus the weighed empty-truck weight on the operator's own "
            "scale tickets, per truck.",
            ["Last ticket", "Truck", "Stored / weighed", "Difference"],
            [row(g["last_at"], f"Truck {g['vehicle_id']}", g["gap"], "kg", g["stored"], max(g["stored"], g["weighed"]),
                 f"{tonnes(g['stored'])} / {tonnes(g['weighed'])} t",
                 f"{abs(round(g['gap']))} kg off" if abs(g["gap"]) >= TARE_GAP_KG else "Within 100 kg",
                 "check" if abs(g["gap"]) >= TARE_GAP_KG else "muted")
             for g in sorted(gaps, key=lambda g: -abs(g["gap"]))])
        finish(c, f"{len(big)} trucks have a stored empty weight {TARE_GAP_KG} kg or more off",
               f"{best['vehicle_id']}: stored {kg(best['stored'])} · weighed {kg(best['weighed'])}"
               if best else "", len(big))
        return {"card": c, "gaps": gaps, "big": big, "serviced": serviced}

    @staticmethod
    def serviced(d: dict) -> list[dict]:
        out = []
        for w in d["work_orders"]:
            if w["work_order_type"] not in SENSOR_WORK:
                continue
            at = ts(w.get("completed_at") or w.get("reported_at"))
            before, after = [], []
            for r in d["rows"].values():
                if r["device_id"] == w["device_id"] and r.get("device_kg") is not None and r.get("ticket_kg") and r["date"]:
                    (before if r["date"] < at.date().isoformat() else after).append(r["device_kg"] - r["ticket_kg"])
            if before and after and abs(mean(after) - mean(before)) > SERVICE_SHIFT_KG:
                out.append({"device_id": w["device_id"], "work": w["work_order_type"].replace("_", " ").lower(),
                            "date": at.date().isoformat(), "before": mean(before), "after": mean(after)})
        return out

    def right_size(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        lease = float((self.params.get("equipment") or {}).get("lease_per_m3_month_eur") or 0)
        hours, side = defaultdict(int), defaultdict(int)
        for x in d["daily"]:
            hours[x["device_id"]] += x.get("hours_full") or 0
        for p in d["pickups"]:
            side[p["device_id"]] += bool(p.get("driver_reported_side_waste"))
        out = []
        for did, dev in d["devices"].items():
            rows = [r for r in d["rows"].values() if r["device_id"] == did and r["pickup_status"] in LIFT_STATUSES]
            if not rows:
                continue
            mat = d["materials"].get(dev.get("material_stream")) or {}
            vol = float(dev.get("container_volume_m3") or 0)
            cap = vol * float(mat.get("typical_compacted_density_kg_m3") or 0)
            kgs = [r["weight_kg"] for r in rows if r["weight_kg"]]
            use = median(kgs) / cap if kgs and cap else None
            cls = dev.get("equipment_class")
            bigger = next((s for s in SIZES if vol < s <= LIMITS.get(cls, 30)), None)
            per_month = len(rows) / d["months"]
            lift = mean(sum(ln["amount_cents"] for ln in r["our_lines"] if ln["line_type"] in LIFT_LINES) for r in rows)
            item = {"device_id": did, "last_at": max((r["date"] or "") for r in rows), "site": FeatureData.site_name(d, did),
                    "class": cls, "volume": vol, "bigger": bigger,
                    "lifts_per_month": per_month, "hours_full": hours[did], "side_waste": side[did], "use": use,
                    "lift_cents": lift, "fits": False}
            if bigger and (hours[did] >= FULL_HOURS or side[did] >= SIDE_WASTE_LIFTS) and use and use > MIN_USE:
                avoided = per_month * 12 * (1 - vol / bigger)
                gross = avoided * lift
                rental = (bigger - vol) * lease * 12 * 100
                item.update(fits=True, avoided=avoided, gross_cents=round(gross), rental_cents=round(rental),
                            saving_cents=round(gross - rental))
            out.append(item)
        fits = [o for o in out if o["fits"]]
        best = max(fits, key=lambda o: o["saving_cents"], default=None)
        ex = None
        if best:
            ex = example(best["site"], best["device_id"], [
                fig("Container now", f"{best['class']} {best['volume']:g} m³", tag="OBSERVED"),
                fig("Suggested size", f"{best['bigger']} m³", tag="ESTIMATED"),
                fig("Hours full", best["hours_full"], "h", "OBSERVED"),
                fig("Side-waste pickups", best["side_waste"], tag="OBSERVED"),
                fig("Typical load", round(100 * best["use"]), "% of capacity", "ESTIMATED"),
                fig("Pickups avoided per year", round(best["avoided"]), tag="ESTIMATED", range_="scaled estimate"),
                fig("Pickup fees avoided per year", round(best["gross_cents"] / 100), "€", "ESTIMATED", "scaled estimate"),
                fig("Extra lease per year", round(best["rental_cents"] / 100), "€", "HYPOTHETICAL"),
                fig("Net saving per year", round(best["saving_cents"] / 100), "€", "ESTIMATED", "scaled estimate"),
            ], [bar("Pickups per year now", best["lifts_per_month"] * 12, "pickups", "ESTIMATED"),
                bar(f"Pickups per year at {best['bigger']} m³", best["lifts_per_month"] * 12 - best["avoided"], "pickups",
                    "ESTIMATED")],
                f"A {best['bigger']} m³ unit would avoid about {best['avoided']:.0f} pickups a year, "
                f"{eur(best['saving_cents'])} a year after the extra lease (scaled estimate).")
        c = card(
            "fleet.right_size", "Equipment right-sizing", "Matches the container size to how much you produce.",
            "Worth a check" if fits else "Good",
            "Containers that are often full or need side-waste pickups may be too small. A larger unit within the "
            "equipment limits means fewer pickups. The saving is the pickup fees avoided minus the extra lease.",
            ("Fill alone cannot tell a light, bulky load from a heavy one that really fills the container.",
             f"{len(fits)} of {len(out)} containers are often full or have side waste while loads are heavy.",
             "Fewer pickups, less side waste and no overflow at the site."),
            ex,
            evidence("ESTIMATED", f"scaled from {d['months']} months; lease {lease:g} €/m³ a month is HYPOTHETICAL",
                     sum(1 for r in d["rows"].values() if r["pickup_status"] in LIFT_STATUSES),
                     "Pickups per month, hours full, side-waste pickups, typical load against the container's capacity, "
                     "pickup fees from your contract, and our lease assumption.",
                     "Size limits: COMBI up to 22 m³, DUO up to 30 m³. This is a proposal to discuss, not a sale."),
            advanced("pickups avoided = pickups per year × (1 − size now ÷ new size); net saving = pickups avoided × "
                     "pickup fees − (new size − size now) × lease per m³ × 12",
                     ["Device", "Site", "Class", "Size m³", "New size m³", "Pickups/month", "Hours full", "Side waste",
                      "Typical load", "Net saving €/yr"],
                     [[o["device_id"], o["site"], o["class"], o["volume"], o["bigger"], round(o["lifts_per_month"], 1),
                       o["hours_full"], o["side_waste"], f"{o['use']:.0%}" if o["use"] else None,
                       round(o["saving_cents"] / 100) if o["fits"] else None]
                      for o in sorted(out, key=lambda o: -(o.get("saving_cents") or -1e9))]))
        total = sum(o["saving_cents"] for o in fits)
        c["details"] = details(
            f"{len(fits)} of {len(out)} containers could go one size up · {eur(total)} a year (estimate)",
            "Pickups avoided = pickups a year × (1 − size now ÷ new size). Net saving = pickup fees avoided minus the "
            f"extra lease ({lease:g} € per m³ a month, our assumption). Scaled from {d['months']} months.",
            ["Last pickup", "Container", "Typical load", "Saving a year"],
            [row(o["last_at"], FeatureData.container(d, o["device_id"]), o.get("saving_cents", 0) / 100 if o["fits"] else None,
                 "€", o["use"] or 0, 1, f"{round(100 * (o['use'] or 0))}% of {o['volume']:g} m³",
                 f"Go to {o['bigger']} m³, {round(o['avoided'])} fewer pickups" if o["fits"] else "Size is fine",
                 "check" if o["fits"] else "muted")
             for o in sorted(out, key=lambda o: (not o["fits"], -(o.get("saving_cents") or 0)))])
        finish(c, f"{len(fits)} containers could go one size up and save {eur(total)} a year",
               f"{best['device_id']}: {best['volume']:g} → {best['bigger']} m³ · about {best['avoided']:.0f} fewer pickups a year"
               if best else "", total)
        return {"card": c, "devices": out, "fits": fits}

    def cards(self, customer_id: str | None = "all") -> dict:
        cards = [self.tare(customer_id)["card"], self.right_size(customer_id)["card"]]
        return {"customer_id": customer_id or "all", "cards": self.decisions.apply(cards)}

    def decide(self, card_id: str, decision: str, customer_id: str | None = "all") -> dict | None:
        return self.decisions.record(self.cards(customer_id)["cards"], card_id, decision)
