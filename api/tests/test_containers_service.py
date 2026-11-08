from datetime import timedelta

from fakes import feature_stack

from app.services.containers_service import current_rule
from app.services.feature_data import ts


def stack():
    return feature_stack()["services"]


def test_rules_respect_max_days_and_site_calendar():
    s = stack()
    d = s.data.load("all")
    res = s.containers.cards("all")
    guard = s.pickups.min_charge("all")
    for c in res["cards"]:
        if c["id"].startswith("containers.weight:"):
            items = [t for t in guard["could_wait"] if t["device_id"] == c["device_id"]]
            assert items and c["estimate"].startswith("≈ ") and c["new_rule"].startswith("Order at ")
            for t in items:
                assert t["gap_days"] + t["extra_days"] <= t["max_days"]
                p = next(p for p in d["pickups"] if p["collection_id"] == t["pickup_id"])
                target = (ts(p["actual_at"]) + timedelta(days=t["extra_days"])).date().isoformat()
                assert (d["calendar"].get((p["site_id"], target)) or {}).get("is_open", True)
    rules = [c for c in res["cards"] if c["kind"] == "rule"]
    assert [c["highlight"] for c in rules] == [i == 0 for i in range(len(rules))]
    assert all(c["sensor"] and c["sensor"]["since"].startswith("since ") for c in res["cards"] if c["kind"] == "sensor")


def test_current_rule_text():
    assert current_rule({"collection_policy": "ON_CALL", "on_call_threshold_pct": 80.0}) == "Order at 80 % full"
    assert current_rule({"collection_policy": "FIXED_SCHEDULE", "fixed_schedule_per_week": 3}) == "Fixed, 3 per week"


def test_approve_only_writes_a_decision():
    s = stack()
    cards = s.containers.cards("all")["cards"]
    if not cards:
        return
    saved = s.containers.decide(cards[0]["id"], "approve", "all")
    assert saved["decision"] == "approve" and saved["evidence"]["new_rule"] == cards[0]["new_rule"]
    assert s.containers.cards("all")["cards"][0]["decision"] == "approve"
    assert s.decisions.history()[0]["chip"] == "Approved"
