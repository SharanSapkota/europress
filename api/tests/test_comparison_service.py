from fakes import FakeRepo, decisions

from app.core.config import Settings
from app.services.comparison_service import ComparisonService
from app.services.our_invoice_service import OurInvoiceService

VERSION = {
    "_id": "CTR-T-V1", "contract_version_id": "CTR-T-V1", "contract_id": "CTR-T", "version_no": 1,
    "effective_from": "2026-01-01", "effective_to": None, "lift_fee_cents": 10000, "per_km_cents": 100,
    "free_km": 0, "contract_km": 10, "remote_surcharge_cents": 0, "fuel_surcharge_bp": 0,
    "haul_fee_cents_per_t": 0, "processing_fee_cents_per_t": 10000, "min_charge_cents": 0, "credit_share_bp": 0,
    "credit_floor_cents_per_t": 0, "contamination_penalty_cents": 0, "rejection_fee_cents_per_t": 0,
    "cancellation_fee_cents": 0, "wasted_trip_fee_cents": 0, "side_waste_fee_cents": 0,
    "emergency_surcharge_cents": 0, "default_weight_kg": 1000,
}


def pickup(n, device_kg):
    return {"_id": f"P{n}", "collection_id": f"P{n}", "device_id": "D1", "contract_id": "CTR-T",
            "operator_job_ref": f"JOB-{n}", "status": "COMPLETED", "trigger_type": "SCHEDULED",
            "actual_at": f"2026-07-0{n}T08:00:00Z", "device_estimated_collected_kg": device_kg}


def ticket(n, kg, loads=1, tare="WEIGHED"):
    return {"_id": f"T{n}", "ticket_id": f"T{n}", "operator_job_ref": f"JOB-{n}", "allocated_net_kg": kg,
            "loads_on_vehicle": loads, "tare_method": tare}


def op_lines(n, kg, ref=None, extra=()):
    ref = ref or f"JOB-{n}"
    base = [("LIFT_FEE", 1, "lift", 10000, 10000), ("TRANSPORT", 10, "km", 100, 1000),
            ("PROCESSING", kg / 1000, "t", 10000, kg * 10)] + list(extra)
    return [{"_id": f"L{n}-{i}", "invoice_line_id": f"L{n}-{i}", "invoice_id": "INV-1", "line_no": i,
             "line_type": t, "service_date": f"2026-07-0{n}", "operator_job_ref": ref, "quantity": q, "unit": u,
             "unit_price_cents": rate, "amount_cents": amt} for i, (t, q, u, rate, amt) in enumerate(base)]


def build():
    pickups = [pickup(1, 1000), pickup(2, 1000), pickup(3, 1000), pickup(4, 800), pickup(5, None), pickup(6, 700),
               pickup(7, 1300), pickup(8, 1000), pickup(9, 1300)]
    tickets = [ticket(1, 1000), ticket(2, 1000), ticket(3, 1000), ticket(4, 500, loads=2), ticket(6, 700),
               ticket(7, 1000), ticket(8, 1000), ticket(9, 1000, tare="STORED")]
    lines = (op_lines(1, 1000) + op_lines(2, 1200)
             + op_lines(3, 1000, extra=[("LIFT_FEE", 1, "lift", 10000, 10000)])
             + op_lines(4, 500) + op_lines(5, 1000) + op_lines(6, 700, ref="JOB-6X") + op_lines(7, 1000) + op_lines(9, 1000))
    lines.append({"_id": "LX", "invoice_line_id": "LX", "invoice_id": "INV-1", "line_no": 99, "line_type": "LIFT_FEE",
                  "service_date": "2026-07-09", "operator_job_ref": "JOB-99", "quantity": 1, "unit": "lift",
                  "unit_price_cents": 10000, "amount_cents": 10000})
    s = Settings()
    ours = OurInvoiceService(
        FakeRepo([{"_id": "D1", "material_stream": "mixed_waste", "has_weight_measurement": True}]),
        FakeRepo(tickets), FakeRepo(), FakeRepo([{"_id": "CTR-T", "contract_id": "CTR-T"}]), FakeRepo([VERSION]),
        FakeRepo(), FakeRepo([{"_id": "mixed_waste", "credit_eligible": False}]), s)
    svc = ComparisonService(FakeRepo(pickups),
                            FakeRepo([{"_id": "INV-1", "invoice_id": "INV-1", "contract_id": "CTR-T",
                                       "billing_period": "2026-07"}]),
                            FakeRepo(lines), decisions(), ours, s)
    return svc, svc.compare("2026-07")


def row(result, pid):
    return next(r for r in result["rows"] if r["pickup_id"] == pid)


def families(r):
    return {(i["family"], i["status"]) for i in r["items"]}


def test_match():
    r = row(build()[1], "P1")
    assert r["status"] == "MATCH" and r["difference_cents"] == 0 and r["match_by"] == "job_ref"
    assert r["sources"]["our_weight"] == "Weighbridge ticket T1" and r["ours"]["estimate"]


def test_weight_gap_billed_vs_ticket_is_check():
    r = row(build()[1], "P2")
    assert r["status"] == "CHECK" and r["operator"]["billed_kg"] == 1200
    assert ("WEIGHT_BASIS_MISMATCH", "CHECK") in families(r) and r["euros_at_stake_cents"] == 2000
    assert r["suggested_action"] == "CORRECT_LINE"


def test_weight_gap_device_vs_ticket_without_cause_is_check():
    r = row(build()[1], "P7")
    assert r["status"] == "CHECK" and ("WEIGHT_DISCREPANCY", "CHECK") in families(r)
    assert "not a combined load" in r["reason"]


def test_duplicate_line():
    _, res = build()
    r = row(res, "P3")
    dup = next(i for i in r["items"] if i["family"] == "DUPLICATE_LINE")
    assert r["status"] == "CHECK" and dup["entity_id"] == "L3-3" and dup["euros_at_stake_cents"] == 10000
    assert res["line_counts"]["DUPLICATE"] == 1


def test_no_lift_line():
    _, res = build()
    assert [u["entity_id"] for u in res["unmatched_lines"]] == ["LX"]
    assert res["line_counts"]["NO_LIFT"] == 1 and res["totals"]["unmatched_cents"] == 10000


def test_combined_load_is_explained():
    r = row(build()[1], "P4")
    assert r["status"] == "EXPLAINED" and "combined load" in r["reason"]


def test_no_ticket_and_no_device_is_no_data():
    r = row(build()[1], "P5")
    assert r["status"] == "NO_DATA" and r["ours"]["weight_source"] == "invoice"
    assert r["suggested_action"] == "REQUEST_TICKET"


def test_typo_fallback_uninvoiced_and_decision_trail():
    svc, res = build()
    assert row(res, "P6")["match_by"] == "contract_date_type" and row(res, "P6")["status"] == "MATCH"
    assert ("UNINVOICED_COLLECTION", "CHECK") in families(row(res, "P8"))
    assert res["counts"] == {"CHECK": 5, "NO_DATA": 1, "EXPLAINED": 1, "MATCH": 2, "DISPUTED": 0}
    saved = svc.decide("P2", "dispute_draft")
    assert saved["decision"] == "dispute_draft" and saved["user"] == "demo user" and saved["created_at"]
    assert saved["suggestion"]["action"] == "CORRECT_LINE" and saved["numbers"]["billed_kg"] == 1200


def test_stored_tare_gap_is_check_with_plain_reason():
    r = row(build()[1], "P9")
    assert r["status"] == "CHECK" and ("WEIGHT_DISCREPANCY", "CHECK") in families(r)
    assert r["reason"] == ("The operator used a stored truck weight. That can explain the gap, "
                           "or the stored weight may be out of date.")
    assert r["draft_question"].startswith("Hello,") and "weighbridge ticket" in r["draft_question"]
