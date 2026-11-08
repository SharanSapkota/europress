from fakes import FakeRepo

from app.core.config import Settings
from app.services.cost_service import CostService

VERSION = {"target_collection_cost_cents_per_t": 10000, "credit_share_bp": 5000, "credit_floor_cents_per_t": 0}


class Names:
    def names(self, site_ids, operator_ids, cid):
        return {"customer_name": "Demo", "site_names": site_ids, "operator_names": operator_ids}


def row(n, kg, collection, lines=(), fill=80, status="COMPLETED", source="ticket", grade="A", device="D1"):
    return {"pickup_id": f"P{n}", "device_id": device, "site_id": "S1", "contract_id": "C1", "contract_version_id": "C1-V1",
            "material": "cardboard", "date": f"2026-07-{n:02d}", "pickup_status": status, "weight_kg": kg,
            "summary": {"collection_cost_cents": collection}, "version": VERSION, "fill_before_pct": fill,
            "ours": {"weight_source": source if kg else None}, "invoice_ids": ["I1"],
            "price_args": {"credit_eligible": True, "grade": grade, "index_cents": 10000},
            "our_lines": [{"line_type": t, "amount_cents": a} for t, a in lines]}


def svc():
    return CostService(Names(), FakeRepo([{"_id": "D1", "collection_policy": "FIXED_SCHEDULE"}]),
                       FakeRepo([{"_id": "S1", "site_name": "Demo site"}]), Settings())


def one(rows):
    return svc().summarize(rows, ["2026-07"], "ORG-1")["containers"][0]


def test_known_weight_gives_collection_cost_per_tonne():
    c = one([row(1, 1000, 15000), row(2, 3000, 25000)])
    assert c["cost_per_t_cents"] == 10000 and c["pickups_with_weight"] == 2
    assert c["weight_sources"] == {"ticket": 2, "invoice": 0, "device": 0}


def test_unknown_weight_is_left_out_and_never_guessed():
    c = one([row(1, None, 15000), row(2, None, 9000)])
    assert c["cost_per_t_cents"] is None and c["ratio"] is None and c["ratio_label"] is None
    c = one([row(1, 1000, 12000), row(2, None, 99999)])
    assert c["cost_per_t_cents"] == 12000 and c["pickups"] == 2 and c["pickups_with_weight"] == 1
    assert "1 pickups without a known weight are left out" in c["sources_text"]


def test_ratio_label_and_headline():
    s = svc()
    assert s.ratio_label(1.19) == "Normal" and s.ratio_label(1.2) == "1.2× normal" and s.ratio_label(1.84) == "1.8× normal"
    res = s.summarize([row(1, 1000, 18000)], ["2026-07"], "ORG-1")
    assert res["containers"][0]["status"] == "CHECK"
    assert res["headline"] == "Cardboard costs 1.8 times the normal rate in your contract."
    assert s.summarize([row(1, 1000, 11000)], ["2026-07"], "ORG-1")["headline"] == "All containers are in the normal range."


def test_confidence_needs_ten_pickups_with_known_weight():
    assert one([row(n, 1000, 10000) for n in range(1, 10)])["confidence"] == "not sure yet"
    assert one([row(n, 1000, 10000) for n in range(1, 11)])["confidence"] == "sure"
    assert one([row(n, None, 10000) for n in range(1, 13)])["confidence"] == "not sure yet"


def test_main_reason_picks_the_biggest_cause():
    low_fill = [row(n, 500, 10000, [("LIFT_FEE", 10000), ("FUEL_SURCHARGE", 500)], fill=28) for n in range(1, 4)]
    assert one(low_fill)["main_reason"].startswith("Pickups happen at about 28% full on a fixed schedule")
    surcharges = [row(n, 500, 10000, [("LIFT_FEE", 10000), ("REMOTE_SURCHARGE", 9000)], fill=28) for n in range(1, 4)]
    assert one(surcharges)["main_reason"].startswith("Surcharges and extra fees add")
    minimum = [row(n, 500, 10000, [("LIFT_FEE", 1000), ("MIN_CHARGE_TOPUP", 5000)]) for n in range(1, 4)]
    assert one(minimum)["main_reason"].startswith("A minimum charge was added on 3 pickups")
    credit = [row(n, 5000, 10000, [("LIFT_FEE", 1000), ("MATERIAL_CREDIT", -10000)], grade="C") for n in range(1, 4)]
    assert one(credit)["main_reason"].startswith("Material credit is")
    assert one([row(1, 1000, 10000, [("LIFT_FEE", 1000)])])["main_reason"].startswith("No single cost stands out")


def test_breakdown_splits_fees():
    c = one([row(1, 1000, 10000, [("LIFT_FEE", 100), ("TRANSPORT", 50), ("PROCESSING", 300), ("FUEL_SURCHARGE", 20),
                                  ("MIN_CHARGE_TOPUP", 30), ("MATERIAL_CREDIT", -400)])])
    assert c["breakdown"] == {"pickup_fees_cents": 150, "weight_fees_cents": 300, "other_charges_cents": 50,
                              "material_credit_cents": -400}


def test_required_lifts_are_not_a_low_fill_cause_and_constraints_are_quantified():
    rows = [dict(row(n, 500, 10000, [("LIFT_FEE", 10000), ("FUEL_SURCHARGE", 500)], fill=28),
                 trigger_type="MAX_INTERVAL_RULE" if n < 3 else "CUSTOMER_REQUEST_PRE_CLOSURE") for n in range(1, 4)]
    s = svc()
    assert not one(rows)["main_reason"].startswith("Pickups happen")
    daily = [{"device_id": "D1", "n_messages": 24, "n_valid_mass": 18, "hours_full": 5}] * 2
    c = s.constraints(rows, {"has_weight_measurement": True}, daily)
    assert c["required_low_fill_pickups"] == 3 and c["hours_full"] == 10 and c["valid_reading_pct"] == 75
    text = s.constraint_text(c)
    assert "3 of 3 low-fill pickups were required" in text and "full for 10 hours" in text and "75%" in text


def test_highlight_is_highest_ratio_with_site_and_plain_reason():
    rows = [row(1, 1000, 18000, lines=[("MIN_CHARGE_TOPUP", 5000)]), row(2, 1000, 31000, device="D2",
            lines=[("MIN_CHARGE_TOPUP", 9000)])]
    res = svc().summarize(rows, ["2026-07"], "ORG-1")
    h = res["highlight"]
    assert h["ratio"] == 3.1 and h["device_id"] == "D2" and res["site_count"] == 1
    assert h["sentence"] == "Cardboard at Demo site costs 3.1 times the normal rate in your contract."
    assert h["reason"] == "Main reason: light pickups that trigger the minimum charge."
    assert res["containers"][0]["benchmark_cents_per_t"] == VERSION["target_collection_cost_cents_per_t"]
    assert svc().summarize([row(1, None, 9000)], ["2026-07"], "ORG-1")["highlight"] is None
