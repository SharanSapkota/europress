from app.core.config import Settings
from app.services.suggestion_service import SuggestionService

GOOD = {k: "GOOD" for k in ("on_time", "missed_visits", "tickets_shared", "lines_to_check", "weight_vs_ours")}
M = {"on_time_rate": 0.69, "missed_visits": 0, "tickets_shared_rate": 0.45, "median_share_lag_days": 23,
     "lines_to_check": 4, "strong_lines": 3, "invoice_lines": 64, "weight_gap_median_pct": 6.0}
S = SuggestionService(Settings())
WORDS = ("fraud", "error", "overcharge")


def action(flags, persistent=(), declined=False, values=None, m=M):
    return S.suggest(dict(GOOD, **flags), list(persistent), declined, values or {}, m)


def test_all_good_needs_no_action():
    tip = action({})
    assert tip["action"] == "NONE" and tip["title"] == "No action needed."
    assert tip["why"] == "All five measures are in a normal range."


def test_priority_order():
    both = {"tickets_shared": "CHECK", "lines_to_check": "CHECK"}
    assert action(both)["action"] == "REQUEST_TICKETS"
    assert action({"lines_to_check": "CHECK"})["action"] == "CORRECT_LINES"
    assert action({"lines_to_check": "CHECK"}, m=dict(M, strong_lines=0))["action"] == "NONE"
    reneg = {"RENEGOTIATE_CONTRACT": 5000}
    assert action(both, ["tickets_shared"], values=reneg)["action"] == "RENEGOTIATE"
    assert action(both, ["tickets_shared"], values={"RENEGOTIATE_CONTRACT": -100})["action"] == "REQUEST_TICKETS"
    tender = {"TENDER_OR_SWITCH_OPERATOR": 9000, **reneg}
    assert action(both, ["tickets_shared"], declined=True, values=tender)["action"] == "TENDER"
    assert action(both, ["tickets_shared"], declined=True, values=reneg)["action"] == "REQUEST_TICKETS"


def test_why_names_the_number_and_drafts_are_polite():
    tip = action({"tickets_shared": "CHECK"})
    assert tip["title"] == "Ask for the missing scale tickets." and "45%" in tip["why"] and tip["why"].endswith(".")
    assert "3 of 64" in action({"lines_to_check": "CHECK"})["why"]
    assert "69%" in action({"on_time": "CHECK"})["why"]
    for a in ("REQUEST_TICKETS", "CORRECT_LINES", "RENEGOTIATE", "TENDER"):
        text = S.draft(a, "Hauler", M)
        assert text.startswith("Hello Hauler") and "Thank you" in text
        assert not any(w in text.lower() for w in WORDS)
    assert S.draft("NONE", "Hauler", M) is None
