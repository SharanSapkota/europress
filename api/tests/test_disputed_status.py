from test_comparison_service import build, row


def test_dispute_draft_keeps_status_and_dispute_sent_marks_disputed_with_time():
    svc, _ = build()
    svc.decide("P2", "dispute_draft")
    r = row(svc.compare("2026-07"), "P2")
    assert r["status"] == "CHECK" and r["decision"] == "dispute_draft" and r["disputed_at"] is None
    svc.decide("P2", "dispute_sent")
    res = svc.compare("2026-07")
    r = row(res, "P2")
    assert r["status"] == "DISPUTED" and r["found_status"] == "CHECK" and r["disputed_at"]
    assert res["counts"]["DISPUTED"] == 1 and res["counts"]["CHECK"] == 2 and res["view_counts"]["disputed"] == 1


def test_unmatched_line_can_be_disputed():
    svc, _ = build()
    svc.decide("LX", "dispute_sent")
    assert svc.compare("2026-07")["unmatched_lines"][0]["status"] == "DISPUTED"


def test_unknown_item_is_not_stored():
    svc, _ = build()
    assert svc.decide("NOPE", "ok") is None
