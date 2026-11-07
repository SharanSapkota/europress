from functools import lru_cache

from fakes import load, real_stack

from app.core.config import Settings
from app.models.schemas import (
    ComparisonResponse,
    CostsResponse,
    OperatorsResponse,
    PrimaryIdeasResponse,
    SecondaryIdeasResponse,
)
from app.services.weight_ideas_service import WeightIdeasService

LEVELS = {"high", "low", "not enough data"}


@lru_cache
def responses():
    comparison, costs, _, scorecard = real_stack()
    invoices = [ComparisonResponse(**comparison.compare(p)).model_dump() for p in comparison.periods()]
    return invoices, CostsResponse(**costs.costs(3)).model_dump(), OperatorsResponse(**scorecard.operators(period="3m")).model_dump()


def check(info, where, needs_reason=False):
    assert info, f"{where}: no explanation"
    assert info["what"], f"{where}: no what"
    assert info["confidence"] in LEVELS, f"{where}: confidence {info['confidence']}"
    assert info["evidence"] in ("observed", "estimated", "simulated", "hypothetical"), f"{where}: no evidence tag"
    assert info["source"] and (info["source"] != "Not enough data" or info["confidence"] == "not enough data"), \
        f"{where}: no source"
    if needs_reason:
        assert info["reason"], f"{where}: no reason"


def walk(node, path="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "why" and isinstance(v, dict) and "source" in v:
                check(v, f"{path}.why")
            elif k in ("why", "suggestion_why") and isinstance(v, dict):
                for name, info in v.items():
                    if isinstance(info, dict):
                        check(info, f"{path}.{k}.{name}")
                if k == "suggestion_why":
                    check(v, f"{path}.{k}")
            else:
                walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]")


def test_every_invoice_number_has_a_source():
    invoices, _, _ = responses()
    for res in invoices:
        walk(res)
        assert set(res["why"]) == {"ours", "operator", "difference"}
        for r in res["rows"]:
            assert {"ours", "operator", "difference"} <= set(r["why"]), r["pickup_id"]
            if r["ours"]["weight_kg"] is not None or r["operator"]["billed_kg"] is not None:
                assert "weight" in r["why"], r["pickup_id"]
            check(r["why"]["difference"], r["pickup_id"], needs_reason=r["status"] != "MATCH")
            for ln in r["lines"]:
                check(ln["why"], f"{r['pickup_id']}.{ln['line_type']}", needs_reason=ln["status"] == "CHECK")
            if r["status"] != "MATCH":
                assert r["cause_text"], r["pickup_id"]
            assert r["trail"]["pickup_id"] == r["pickup_id"] and r["trail"]["contract_version_id"] == r["contract_version_id"]
            if r["invoice_ids"]:
                assert r["trail"]["invoice_line_ids"], r["pickup_id"]
        for u in res["unmatched_lines"]:
            check(u["why"]["amount"], u["entity_id"], needs_reason=True)
            assert u["cause"] == "invoice" and u["trail"]["invoice_line_ids"] == [u["entity_id"]]


def test_every_cost_number_has_a_source():
    _, costs, _ = responses()
    walk(costs)
    for c in costs["containers"]:
        assert set(c["why"]) == {"cost_per_t", "benchmark", "ratio", "pickups", "pickup_fees", "weight_fees",
                                 "material_credit", "main_reason"}, c["device_id"]
        check(c["why"]["main_reason"], c["device_id"], needs_reason=True)
        check(c["why"]["ratio"], c["device_id"], needs_reason=True)


def test_every_operator_measure_and_suggestion_has_a_source():
    _, _, ops = responses()
    walk(ops)
    for card in ops["operators"]:
        check(card["suggestion_why"], card["operator_id"], needs_reason=True)
        for m in card["measures"]:
            check(m["why"], f"{card['operator_id']}.{m['key']}", needs_reason=m["status"] == "CHECK")


def test_every_weight_idea_number_has_a_source():
    comparison, _, _, _ = real_stack()
    repos = {n: load(n) for n in ("collection_events", "weighbridge_tickets", "devices", "sites", "contracts",
                                  "contract_versions", "material_classes", "maintenance_work_orders", "decision_cases")}
    svc = WeightIdeasService(
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
        Settings(),
    )
    prim = PrimaryIdeasResponse(**svc.primary_ideas("all")).model_dump()
    sec = SecondaryIdeasResponse(**svc.secondary_ideas("all")).model_dump()
    walk(prim)
    walk(sec)
