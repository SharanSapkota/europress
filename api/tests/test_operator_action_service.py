from fakes import real_stack

from app.services.operator_action_service import FEE_FIELDS, OperatorActionService, peer_terms


def test_choose_keeps_positive_values_and_one_contract_action():
    v = {"DISPUTE_INVOICE": {"value_cents": 100}, "REQUEST_WEIGHBRIDGE_DATA": {"value_cents": -20},
         "RENEGOTIATE_CONTRACT": {"value_cents": 500}, "TENDER_OR_SWITCH_OPERATOR": {"value_cents": 900}}
    assert OperatorActionService.choose(v) == ["DISPUTE_INVOICE", "TENDER_OR_SWITCH_OPERATOR"]
    assert OperatorActionService.choose({}) == []


def test_peer_terms_need_enough_other_contracts():
    row = {"region_code": "R", "material_stream": "m", "pricing_model": "p", "bucket": "S",
           "version": {f: 10 for f in FEE_FIELDS + ["credit_share_bp", "free_km"]}}
    assert peer_terms([row] * 4, row) == (None, None)
    assert peer_terms([row] * 5, row)[1] == "L1"


def test_cases_only_choose_candidate_actions():
    _, _, actions, _ = real_stack()
    cases = [{"case_id": "OC-T", "contract_id": "CTR-00011", "candidate_actions": "DISPUTE_INVOICE",
              "as_of_at": "2026-10-13T09:00:00Z"}]
    out = actions.cases(cases)[0]
    assert set(out["values"]) == {"DISPUTE_INVOICE"} and out["actions"] in ("", "DISPUTE_INVOICE")
