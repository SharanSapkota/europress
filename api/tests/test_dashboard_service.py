from fakes import feature_stack

from app.services.dashboard_service import LINKS


def stack():
    return feature_stack()["services"]


def test_dashboard_has_totals_three_tiles_and_no_alerts():
    res = stack().dashboard.dashboard("all")
    assert [t["key"] for t in res["tiles"]] == ["to_check", "disputed", "cost_per_t"]
    assert res["tiles"][0]["label"] == "Lifts to check"
    assert "alerts" not in res and "alert_count" not in res
    if res["period"]:
        assert res["period"] == res["periods"][-1]
        assert set(res["why"]) >= {"ours", "operator", "difference"}
        assert res["totals"]["difference_cents"] == res["totals"]["operator_cents"] - res["totals"]["ours_cents"]
    assert all("ORG-" not in s["name"] for s in res["sites"])


def test_unknown_period_falls_back_to_latest():
    svc = stack().dashboard
    res = svc.dashboard("all", "1999-01")
    assert res["period"] == (res["periods"][-1] if res["periods"] else None)


def test_next_decision_is_highest_yearly_value_and_skips_decided():
    s = stack()
    cands = s.dashboard.candidates("all")
    nxt = s.dashboard.next_decision("all")
    if not cands:
        assert nxt is None
        return
    best = max(cands, key=lambda c: c["per_year"])
    assert nxt["id"] == best["id"] and nxt["link"] == LINKS[best["id"]]
    assert nxt["estimate"].endswith("(estimate).") and "ORG-" not in nxt["sentence"]
    decide = s.pickups.decide if best["id"].startswith("pickups.") else s.fleet.decide
    decide(best["id"], "prepare", "all")
    after = s.dashboard.next_decision("all")
    assert after is None or after["id"] != best["id"]
