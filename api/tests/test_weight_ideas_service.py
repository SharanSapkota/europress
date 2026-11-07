from fakes import load, real_stack
from test_explain import walk

from app.core.config import Settings
from app.models.schemas import PrimaryIdeasResponse, SecondaryIdeasResponse
from app.services.weight_ideas_service import WeightIdeasService

BANNED_PHRASES = ("inflated tonnage", "fraud", "premium smart", "premium service", "cheating", "dishonest", "steal")


def build_service():
    comparison, _, _, _ = real_stack()
    s = Settings()
    repos = {n: load(n) for n in ("collection_events", "weighbridge_tickets", "devices", "sites", "contracts",
                                  "contract_versions", "material_classes", "maintenance_work_orders", "decision_cases")}
    return WeightIdeasService(
        comparison,
        repos["collection_events"],
        repos["weighbridge_tickets"],
        repos["devices"],
        repos["sites"],
        repos["contracts"],
        repos["contract_versions"],
        repos["material_classes"],
        repos["maintenance_work_orders"],
        repos["decision_cases"],
        comparison.decisions,
        s,
    )


def test_primary_ideas_schema_and_explainability():
    svc = build_service()
    res = PrimaryIdeasResponse(**svc.primary_ideas("all")).model_dump()
    walk(res)
    assert len(res["idea5_sorting"]) > 0
    assert len(res["idea3_residual"]) > 0
    assert len(res["idea6_combined"]) > 0
    # Verify Idea 3 separates calibration offset from physical residual
    classes = {r["classification"] for r in res["idea3_residual"]}
    assert "PHYSICAL_RESIDUAL" in classes
    assert "CALIBRATION_OFFSET" in classes
    # Verify Idea 6 proportional reallocation preserves total truck net_kg
    for pair in res["idea6_combined"]:
        assert pair["proportional_a_kg"] + pair["proportional_b_kg"] == pair["truck_net_kg"]


def test_secondary_ideas_schema_and_explainability():
    svc = build_service()
    res = SecondaryIdeasResponse(**svc.secondary_ideas("all")).model_dump()
    walk(res)
    assert len(res["idea1_mass_trigger"]) > 0
    assert len(res["idea2_day0_receipt"]) > 0
    assert len(res["idea4_deconvolution"]) > 0
    assert len(res["idea7_rightsizer"]) > 0
    assert len(res["business_case"]["tiers"]) == 3
    assert len(res["business_case"]["sensitivity"]) == 5
    sides = {r["source_side"] for r in res["idea4_deconvolution"]}
    assert sides == {"HAULER_STORED_TARE", "COMPACTOR_SENSOR_CALIBRATION"}


def test_no_banned_phrases_and_human_approval_undo():
    svc = build_service()
    prim = svc.primary_ideas("all")
    sec = svc.secondary_ideas("all")
    all_rows = (prim["idea5_sorting"] + prim["idea3_residual"] + prim["idea6_combined"] +
                sec["idea1_mass_trigger"] + sec["idea2_day0_receipt"] + sec["idea4_deconvolution"] +
                sec["idea7_rightsizer"])
    for r in all_rows:
        blob = f"{r['suggestion']} {r['reason']} {r.get('_draft') or ''}".lower()
        for phrase in BANNED_PHRASES:
            assert phrase not in blob, f"Banned phrase '{phrase}' in {r['item_id']}"
    first_id = prim["idea5_sorting"][0]["item_id"]
    saved = svc.decide(first_id, "prepare", "all")
    assert saved is not None and saved["decision"] == "prepare" and saved["draft"]
    updated = svc.primary_ideas("all")["idea5_sorting"][0]
    assert updated["decision"] == "prepare" and updated["draft"]
    svc.decisions.undo(saved["decision_id"])
    after_undo = svc.primary_ideas("all")["idea5_sorting"][0]
    assert after_undo["decision"] is None
