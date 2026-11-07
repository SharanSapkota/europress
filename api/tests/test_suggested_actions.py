from test_comparison_service import build, row

from app.services.comparison_service import STORED_TARE_REASON


def test_line_fault_with_agreeing_ticket_asks_to_correct_line():
    res = build()[1]
    assert row(res, "P2")["suggested_action"] == "CORRECT_LINE"
    assert row(res, "P3")["suggested_action"] == "CORRECT_LINE"
    assert res["unmatched_lines"][0]["suggested_action"] == "CORRECT_LINE"


def test_no_ticket_asks_for_scale_ticket():
    res = build()[1]
    assert row(res, "P5")["suggested_action"] == "REQUEST_TICKET"
    assert row(res, "P7")["suggested_action"] == "REQUEST_TICKET"


def test_explained_and_match_need_no_action():
    res = build()[1]
    assert row(res, "P4")["suggested_action"] == "NONE" and row(res, "P4")["draft_question"] is None
    assert row(res, "P1")["suggested_action"] == "NONE"


def test_every_item_explains_what_why_and_how_sure_in_one_sentence_each():
    res = build()[1]
    for r in res["rows"] + res["unmatched_lines"]:
        for part in ("what", "why", "how_sure"):
            text = r["explain"][part]
            if text == STORED_TARE_REASON:
                continue
            assert text and text.endswith(".") and text.count(". ") == 0, (r.get("pickup_id"), part, text)
    assert row(res, "P5")["explain"]["how_sure"].startswith("Not sure")
