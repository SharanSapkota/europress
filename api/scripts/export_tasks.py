import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controllers.deps import unscoped
from app.services.matching_service import MatchingService

A_COLS = ["collection_cost", "processing_cost", "penalties", "material_credit", "net_material_contribution",
          "total_customer_cost"]


def eur(c):
    return "" if c is None else f"{c / 100:.2f}"


def export(out: Path) -> tuple[int, int]:
    svc = unscoped().comparison
    out.mkdir(parents=True, exist_ok=True)
    periods = svc.invoices.periods()
    pickups = svc.pickups.all()
    invoices = [i for p in periods for i in svc.invoices.by_period(p)]
    lines = svc.lines.by_invoices([i["invoice_id"] for i in invoices])
    by_pickup = MatchingService(svc.s.local_tz).match(invoices, lines, pickups)["by_pickup"]

    with (out / "my_task_a.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["collection_id"] + [f"{c}_eur" for c in A_COLS] + ["collection_cost_eur_per_t",
                    "total_cost_eur_per_t", "billing_mass_kg", "mass_source"])
        for p in pickups:
            o = svc.ours.for_pickup(p, by_pickup.get(p["collection_id"], []))
            s = o["summary"]
            w.writerow([p["collection_id"]] + [eur(s[f"{c}_cents"]) for c in A_COLS] +
                       [eur(s["collection_cost_cents_per_t"]), eur(s["total_cost_cents_per_t"]),
                        o["weight"]["kg"] if o["weight"]["kg"] is not None else "", o["weight"]["source"] or ""])

    invoiced = set(by_pickup)
    items = []
    for period in periods:
        res = svc.compare(period, everyone=True)
        items += res["unmatched_lines"]
        for r in res["rows"]:
            items += [i for i in r["items"]
                      if not (i["family"] == "UNINVOICED_COLLECTION" and r["pickup_id"] in invoiced)]
    seen, b_rows = set(), []
    for i in items:
        key = (i["entity_type"], i["entity_id"], i["family"])
        if i["status"] == "CHECK" and key not in seen:
            seen.add(key)
            b_rows.append(i)
    with (out / "my_task_b.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_type", "entity_id", "label_family", "status", "euros_at_stake_estimate", "confidence",
                    "reason"])
        for i in b_rows:
            w.writerow([i["entity_type"], i["entity_id"], i["family"], i["status"], eur(i["euros_at_stake_cents"]),
                        i["confidence"], i["reason"]])
    return len(pickups), len(b_rows)


if __name__ == "__main__":
    a, b = export(Path(sys.argv[1] if len(sys.argv) > 1 else "api/exports"))
    print(f"my_task_a.csv {a} rows, my_task_b.csv {b} rows")
