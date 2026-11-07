import csv
from pathlib import Path

from fakes import load

from app.core.config import Settings
from app.services.matching_service import MatchingService
from app.services.our_invoice_service import OurInvoiceService

KEY = Path(__file__).parent / "fixtures" / "labels_dev_reference_economics.csv"
COLS = [("collection_cost_eur", "collection_cost_cents"), ("processing_cost_eur", "processing_cost_cents"),
        ("penalties_eur", "penalties_cents"), ("material_credit_eur", "material_credit_cents"),
        ("net_material_contribution_eur", "net_material_contribution_cents"),
        ("total_customer_cost_eur", "total_customer_cost_cents"),
        ("collection_cost_eur_per_t", "collection_cost_cents_per_t"), ("total_cost_eur_per_t", "total_cost_cents_per_t")]


def setup():
    s = Settings()
    svc = OurInvoiceService(load("devices"), load("weighbridge_tickets"), load("quality_assessments"), load("contracts"),
                            load("contract_versions"), load("price_index_monthly"), load("material_classes"), s)
    pickups = load("collection_events")
    m = MatchingService(s.local_tz).match(load("invoices").all(), load("invoice_lines").all(),
                                          pickups.all())
    return svc, pickups, m["by_pickup"]


def cents(v):
    return None if v == "" else round(float(v) * 100)


def test_matches_answer_key_to_the_cent_on_every_covered_row():
    svc, pickups, lines = setup()
    covered = uncovered = 0
    for r in csv.DictReader(KEY.open()):
        ours = svc.for_pickup(pickups.get(r["collection_id"]), lines.get(r["collection_id"], []))
        assert ours["contract_version_id"] == r["contract_version_id"]
        assert ours["service_date"] == r["service_date"]
        ref_kg = None if r["billing_mass_kg"] == "" else round(float(r["billing_mass_kg"]))
        if ref_kg is not None and ours["weight"]["kg"] != ref_kg:
            uncovered += 1
            assert ours["weight"]["source"] in ("device", "invoice")
            continue
        covered += 1
        for ref_col, our_col in COLS:
            if ref_kg is None and our_col.endswith("_per_t"):
                continue
            assert cents(r[ref_col]) == ours["summary"][our_col], (r["collection_id"], ref_col)
    assert covered == 209 and uncovered == 5


def test_real_pickup_uses_ticket_weight():
    svc, pickups, lines = setup()
    ours = svc.for_pickup(pickups.get("COL-00001-0001"), lines["COL-00001-0001"])
    assert ours["weight"] == {"kg": 520, "source": "ticket", "range_kg": 0, "source_id": "WB-OP-E-00001-0001",
                              "confidence": "high"}
    assert ours["total_cents"] == 29020


def test_unknown_weight_is_never_guessed():
    svc, pickups, _ = setup()
    p = dict(pickups.get("COL-00001-0001"), operator_job_ref="NONE", device_estimated_collected_kg=None)
    ours = svc.for_pickup(p, [])
    assert ours["weight"]["kg"] is None and ours["lower_bound"]
    assert ours["summary"]["collection_cost_cents_per_t"] is None
    assert not any(ln["line_type"] == "PROCESSING" for ln in ours["lines"])
