from collections import defaultdict
from statistics import median

from app.services.cards import advanced, bar, card, details, eur, evidence, example, fig, finish, kg, row, tonnes
from app.services.feature_data import FeatureData, FeatureDecisions, ts
from app.services.pricing import LIFT_STATUSES, rhu

SENSOR_WORK = ("SENSOR_RECALIBRATION", "SENSOR_REPLACEMENT")
LEFT_SHARE = 0.15
LIGHT, HEAVY = 0.85, 1.15


def left_hits(pickups: list[dict], work_orders: list[dict]) -> tuple[list[dict], list[dict]]:
    work = defaultdict(list)
    for w in work_orders:
        if w["work_order_type"] in SENSOR_WORK:
            work[w["device_id"]].append(ts(w.get("completed_at") or w.get("reported_at")))
    hits, baseline = [], []
    for p in pickups:
        before, after = p.get("device_mass_kg_before"), p.get("device_mass_kg_after")
        partial = p["status"] == "PARTIAL" or p.get("driver_reported_partial")
        heavy = before and after is not None and before > 0 and after > LEFT_SHARE * before
        if p["status"] not in LIFT_STATUSES or not (partial or heavy):
            continue
        at = ts(p.get("actual_at"))
        near = any(w and at and abs((at - w).days) <= 7 for w in work[p["device_id"]])
        (baseline if near else hits).append(p)
    return hits, baseline


class SiteChecksService:
    def __init__(self, data: FeatureData, decisions):
        self.data = data
        self.decisions = FeatureDecisions(decisions)

    def left_in_container(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        hits, baseline = left_hits(d["pickups"], d["work_orders"])
        best = max(hits, key=lambda p: p.get("device_mass_kg_after") or 0, default=None)
        ex = None
        if best:
            before, after = best["device_mass_kg_before"], best.get("device_mass_kg_after") or 0
            ex = example(FeatureData.site_name(d, best["device_id"]), best["device_id"], [
                fig("Pickup", best["collection_id"], tag="OBSERVED"),
                fig("Weight before pickup", round(before), "kg", "ESTIMATED", "± 3.3 %"),
                fig("Weight after pickup", round(after), "kg", "ESTIMATED", "± 3.3 %"),
                fig("Share left", round(100 * after / before), "%", "ESTIMATED"),
                fig("Pickup status", best["status"].capitalize(), tag="OBSERVED"),
            ], [bar("Weight before pickup", before, "kg", "ESTIMATED"), bar("Weight after pickup", after, "kg", "ESTIMATED")],
                f"{round(after)} kg ({after / before:.0%}) of material stayed in the container after this pickup.")
        c = card(
            "site_checks.left_in_container", "Material left after pickup",
            "Makes sure you get the full pickup you pay for.",
            "Worth a check" if hits else "Good",
            "After a normal pickup the container is close to empty. The container weight before and after each "
            "pickup shows when a lot of material stayed in it. We do not claim a cause; it is a point to check "
            "with the site and the driver.",
            ("The fill reading drops after a pickup even when material stays stuck at the back.",
             f"{len(hits)} pickups left more than {LEFT_SHARE:.0%} of the weight in the container.",
             "A full pickup for the same fee, and fewer extra pickups soon after."),
            ex,
            evidence("ESTIMATED", "weights ± 3.3 %", len(hits),
                     "Container weight before and after each pickup and the pickup status. Pickups within 7 days of "
                     f"a sensor service are left out as sensor baseline ({len(baseline)}).",
                     "Material can stay in the container for many reasons, such as frozen or wet loads. This is not "
                     "a claim about the operator."),
            advanced(f"flag when weight after > {LEFT_SHARE:.0%} × weight before, or the pickup is partial; "
                     "leave out pickups within 7 days of a sensor recalibration or replacement",
                     ["Pickup", "Site", "Before kg", "After kg", "Share left", "Status"],
                     [[p["collection_id"], FeatureData.site_name(d, p["device_id"]), round(p["device_mass_kg_before"] or 0),
                       round(p.get("device_mass_kg_after") or 0),
                       f"{(p.get('device_mass_kg_after') or 0) / max(1, p['device_mass_kg_before'] or 1):.0%}",
                       p["status"].capitalize()] for p in sorted(hits, key=lambda p: -(p.get("device_mass_kg_after") or 0))]))
        c["details"] = details(
            f"{len(hits)} pickups left over {LEFT_SHARE:.0%} of the material · {len(baseline)} left out after a sensor service",
            f"Flagged when more than {LEFT_SHARE:.0%} of the weight stays in the container after a pickup, or the pickup "
            "is partial. Pickups within 7 days of a sensor service are left out. Weights ± 3.3 %.",
            ["Date", "Container", "Left after pickup", "Left"],
            [row(p.get("actual_at"), FeatureData.container(d, p["device_id"]), p.get("device_mass_kg_after") or 0, "kg",
                 p.get("device_mass_kg_after") or 0, p.get("device_mass_kg_before") or 0,
                 f"{tonnes(p.get('device_mass_kg_after') or 0)} / {tonnes(p.get('device_mass_kg_before') or 0)} t",
                 "Partial pickup" if p["status"] == "PARTIAL" else
                 f"{(p.get('device_mass_kg_after') or 0) / max(1, p.get('device_mass_kg_before') or 1):.0%} stayed",
                 "check") for p in sorted(hits, key=lambda p: -(p.get("device_mass_kg_after") or 0))])
        finish(c, f"{len(hits)} pickups left more than {LEFT_SHARE:.0%} of the material in the container",
               f"{best['collection_id']}: {kg(best['device_mass_kg_before'])} before · "
               f"{kg(best.get('device_mass_kg_after') or 0)} after" if best else "", len(hits))
        return {"card": c, "hits": hits}

    def shared_split(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        groups = defaultdict(list)
        for t in d["tickets"]:
            if t.get("allocation_method") == "EQUAL_SPLIT_COMBINED_LOAD":
                groups[t["weighing_event_id"]].append(t)
        moves, events = [], 0
        for wid, tickets in sorted(groups.items()):
            parts = []
            for t in tickets:
                p = d["by_job"].get(t["operator_job_ref"])
                r = d["rows"].get(p["collection_id"]) if p else None
                if r and r.get("device_kg") and r["version"]:
                    v = r["version"]
                    parts.append((t, p, r["device_kg"], int(v["haul_fee_cents_per_t"] or 0) + int(v["processing_fee_cents_per_t"] or 0)))
            if len(parts) < 2:
                continue
            events += 1
            net = sum(t["allocated_net_kg"] for t, *_ in parts)
            total_dev = sum(dev for _, _, dev, _ in parts)
            for t, p, dev, rate in parts:
                fair = net * dev / total_dev
                moved = fair - t["allocated_net_kg"]
                moves.append({"event": wid, "pickup_id": p["collection_id"], "site": FeatureData.site_name(d, p["device_id"]),
                              "device_id": p["device_id"], "customer_id": p.get("customer_id"),
                              "equal_kg": t["allocated_net_kg"], "fair_kg": fair, "kg": moved,
                              "cents": rhu(round(moved) * rate, 1000), "rate": rate})
        total_kg = sum(abs(m["kg"]) for m in moves) / 2
        total_cents = sum(abs(m["cents"]) for m in moves) // 2
        best = max(moves, key=lambda m: abs(m["cents"]), default=None)
        ex = None
        if best:
            pair = [m for m in moves if m["event"] == best["event"]]
            gain = next(m for m in pair if m["kg"] > 0)
            net_cents = sum(m["cents"] for m in pair)
            ex = example(", ".join(m["site"] for m in pair), ", ".join(m["device_id"] for m in pair),
                         [fig("Shared weighing", best["event"], tag="OBSERVED")] +
                         [fig(f"{m['site']} change", f"{m['kg']:+.0f} kg ({m['cents'] / 100:+.0f} €)", tag="ESTIMATED")
                          for m in pair] +
                         [fig("Net difference from different contract rates", round(net_cents / 100), "€", "ESTIMATED")],
                         [bar(f"Equal split for {gain['site']}", gain["equal_kg"], "kg", "OBSERVED"),
                          bar(f"Split by container weight for {gain['site']}", gain["fair_kg"], "kg", "ESTIMATED")],
                         f"Splitting by container weight moves {abs(best['kg']):.0f} kg between your own sites; the "
                         f"euro amounts differ by {abs(net_cents) / 100:.0f} € because each site has its own contract rates.")
        same = all(len({m["customer_id"] for m in moves if m["event"] == e}) == 1 for e in {m["event"] for m in moves})
        c = card(
            "site_checks.shared_split", "Shared truck split",
            "Gives each of your sites its fair share of a shared truck load.",
            "Worth a check" if moves else "Not enough data",
            "When two of your containers go on one truck, the operator weighs the truck once and splits the weight "
            "equally. Your container weights show how much each site really sent. That gives a fairer cost split "
            "between your own sites.",
            ("Fill readings cannot tell two loads on one truck apart.",
             f"{events} shared weighings; splitting by container weight moves {round(total_kg):,} kg between sites.".replace(",", "\u00a0"),
             f"About {eur(total_cents)} of cost moves to the site that sent the material (estimate)."),
            ex,
            evidence("ESTIMATED", "weights ± 3.3 %", 2 * events,
                     "Shared weighings on scale tickets, container weight at each pickup and each site's contract fees "
                     "per tonne." + ("" if same else " Some shared loads mix customers."),
                     "This is about your own sites' cost split, not an operator mistake."),
            advanced("site share = truck net weight × container weight ÷ sum of container weights on the truck; "
                     "euro change = weight change × the site's haul and processing fee per tonne",
                     ["Weighing", "Pickup", "Site", "Equal split kg", "By weight kg", "Change kg", "Change €"],
                     [[m["event"], m["pickup_id"], m["site"], round(m["equal_kg"]), round(m["fair_kg"]), round(m["kg"]),
                       round(m["cents"] / 100)] for m in moves]))
        dates = {r["pickup_id"]: r["date"] for r in d["rows"].values()}
        c["details"] = details(
            f"{events} shared loads · {kg(total_kg)} moved between your sites · {eur(total_cents)} (estimate)",
            "Each site's share = the truck's weight × its container weight ÷ all container weights on the truck. "
            "The operator splits it equally. Weights ± 3.3 %.",
            ["Date", "Container", "Equal split → by weight", "Change"],
            [row(dates.get(m["pickup_id"]), FeatureData.container(d, m["device_id"]), m["cents"] / 100, "€",
                 m["fair_kg"], max(m["fair_kg"], m["equal_kg"]), f"{tonnes(m['equal_kg'])} → {tonnes(m['fair_kg'])} t",
                 f"{m['kg']:+.0f} kg".replace("-", "−"), "check" if m["kg"] > 0 else "muted")
             for m in sorted(moves, key=lambda m: -abs(m["cents"]))])
        finish(c, f"{kg(total_kg)} of shared truck loads belongs to another of your sites",
               f"{best['event']}: {kg(abs(best['kg']))} moves between " +
               " and ".join(m["site"].split(" (")[0] for m in moves if m["event"] == best["event"]) if best else "",
               total_cents)
        return {"card": c, "moves": moves, "total_kg": total_kg, "total_cents": total_cents}

    def density(self, customer_id: str | None = "all") -> dict:
        d = self.data.load(customer_id)
        out = []
        for did, dev in d["devices"].items():
            mat = dev.get("material_stream")
            if mat not in ("mixed_waste", "cardboard", "paper") or not dev.get("has_weight_measurement"):
                continue
            vol = float(dev.get("container_volume_m3") or 0)
            dens = [p["device_mass_kg_before"] / (p["device_fill_pct_before"] / 100 * vol)
                    for p in d["pickups"] if p["device_id"] == did and p["status"] in LIFT_STATUSES and vol
                    and (p.get("device_mass_kg_before") or 0) > 0 and (p.get("device_fill_pct_before") or 0) >= 10]
            if len(dens) < 5:
                continue
            typical = float(d["materials"][mat]["typical_compacted_density_kg_m3"])
            ratio = median(dens) / typical
            note = ("Lighter than normal. This often means light packaging is in the general waste. Worth a check."
                    if mat == "mixed_waste" and ratio < LIGHT else
                    "Heavier than normal. On outdoor staging sites this is often wet material."
                    if mat in ("cardboard", "paper") and ratio > HEAVY else "Within the normal range.")
            last = max((p.get("actual_at") or "" for p in d["pickups"] if p["device_id"] == did), default=None)
            out.append({"device_id": did, "site": FeatureData.site_name(d, did), "site_id": dev.get("site_id"),
                        "last_at": last, "material": mat, "lifts": len(dens),
                        "median": median(dens), "typical": typical, "ratio": ratio, "note": note,
                        "flag": note != "Within the normal range."})
        mixed = [o for o in out if o["material"] == "mixed_waste"]
        best = min(mixed, key=lambda o: o["ratio"], default=None)
        light = [o for o in mixed if o["ratio"] < LIGHT]
        heavy = [o for o in out if o["material"] in ("cardboard", "paper") and o["ratio"] > HEAVY]
        ex = None
        if best:
            ex = example(best["site"], best["device_id"], [
                fig("Weighed pickups", best["lifts"], tag="OBSERVED"),
                fig("Density at pickup (median)", round(best["median"]), "kg/m³", "ESTIMATED", "± 3.3 %"),
                fig("Normal for mixed waste", round(best["typical"]), "kg/m³", "OBSERVED"),
                fig("Compared with normal", round(100 * best["ratio"]), "%", "ESTIMATED"),
            ], [bar("Normal for mixed waste", best["typical"], "kg/m³", "OBSERVED"),
                bar("Measured at pickup", best["median"], "kg/m³", "ESTIMATED")], best["note"])
        c = card(
            "site_checks.density", "Density check", "Spots general waste that looks lighter or heavier than normal.",
            "Worth a check" if out else "Not enough data",
            "Weight divided by how full the container is gives the density at pickup. General waste that is much "
            "lighter than normal often holds light packaging. Cardboard that is much heavier than normal is often wet.",
            ("A full container looks the same whether it holds heavy or light material.",
             f"{len(light)} mixed-waste containers are below {LIGHT:.0%} of normal; {len(heavy)} cardboard containers are "
             f"above {HEAVY:.0%}.",
             "A short site check can show if packaging goes in the wrong bin or cardboard gets wet."),
            ex,
            evidence("ESTIMATED", "density ± 3.3 %", sum(o["lifts"] for o in out),
                     "Container weight and fill before each pickup, the container size and the normal density for "
                     "the material. Only containers with 5 or more weighed pickups.",
                     "Density shows how the material is sorted and stored at your site. It says nothing about the "
                     "operator. No saving is claimed."),
            advanced("density = weight before pickup ÷ (fill before pickup × container size); compared with the "
                     "material's normal density; containers with 5+ weighed pickups",
                     ["Device", "Site", "Material", "Pickups", "Median kg/m³", "Normal kg/m³", "Compared", "Note"],
                     [[o["device_id"], o["site"], o["material"].replace("_", " "), o["lifts"], round(o["median"]),
                       round(o["typical"]), f"{o['ratio']:.0%}", o["note"]] for o in sorted(out, key=lambda o: o["ratio"])]))
        c["details"] = details(
            f"{len(out)} containers checked · {len(light)} light general waste · {len(heavy)} heavy cardboard",
            "Density = weight ÷ (how full × container size), the median over weighed pickups, compared with the normal "
            "density for the material. Weights ± 3.3 %.",
            ["Last pickup", "Container", "Density", "Compared"],
            [row(o.get("last_at"), FeatureData.container(d, o["device_id"]), 100 * o["ratio"], "%", o["median"],
                 max(o["median"], o["typical"]), f"{round(o['median'])} / {round(o['typical'])} kg/m³",
                 o["note"].split(".")[0], "check" if o["flag"] else "muted")
             for o in sorted(out, key=lambda o: (not o["flag"], o["ratio"]))])
        finish(c, f"{len(light)} general waste containers are lighter than normal, {len(heavy)} cardboard heavier",
               f"{best['device_id']}: {round(best['median'])} kg/m³ vs normal {round(best['typical'])} kg/m³"
               if best else "", 0)
        return {"card": c, "devices": out}

    def cards(self, customer_id: str | None = "all") -> dict:
        cards = [self.left_in_container(customer_id)["card"], self.shared_split(customer_id)["card"],
                 self.density(customer_id)["card"]]
        return {"customer_id": customer_id or "all", "cards": self.decisions.apply(cards)}

    def decide(self, card_id: str, decision: str, customer_id: str | None = "all") -> dict | None:
        return self.decisions.record(self.cards(customer_id)["cards"], card_id, decision)
