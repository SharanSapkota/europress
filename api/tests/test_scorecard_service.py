from functools import lru_cache

from fakes import real_stack

from app.core.config import Settings
from app.services.scorecard_service import ScorecardService

S = Settings()
WEIGHED = {"has_weight_measurement": True}


def svc():
    return ScorecardService(None, None, None, None, None, None, None, None, None, None, S)


def pickup(status="COMPLETED", sched="2026-07-01T08:00:00Z", actual="2026-07-01T09:00:00Z", dev=1000):
    return {"operator_id": "OP", "status": status, "scheduled_at": sched, "actual_at": actual,
            "order_placed_at": None, "device_estimated_collected_kg": dev}


def ticket(kg=1100, loads=1, arrival="2026-07-01T10:00:00Z", published="2026-07-03T10:00:00Z"):
    return {"allocated_net_kg": kg, "loads_on_vehicle": loads, "arrival_at": arrival, "published_at": published}


def metrics(jobs):
    return ScorecardService.metrics(jobs, [], [])


def test_on_time_uses_the_configured_window():
    s = svc()
    near = s.job(pickup(actual="2026-07-01T20:00:00Z"), None, None, "R", 24)
    late = s.job(pickup(actual="2026-07-02T09:00:00Z"), None, None, "R", 24)
    assert near["on_time"] and not late["on_time"]
    assert not s.job(pickup(actual="2026-07-01T20:00:00Z"), None, None, "R", 2)["on_time"]
    assert metrics([near, late])["on_time_rate"] == 0.5


def test_missed_visits_ignore_low_fill_skips_and_customer_cancellations():
    s = svc()
    jobs = [s.job(pickup(status=st, actual=None), None, None, "R", 24)
            for st in ("MISSED_BY_OPERATOR", "WASTED_TRIP")]
    assert metrics(jobs)["missed_visits"] == 1
    from app.services.scorecard_service import OPERATOR_STATUSES
    assert "SKIPPED_LOW_FILL" not in OPERATOR_STATUSES and "CANCELLED_BY_CUSTOMER" not in OPERATOR_STATUSES


def test_ticket_share_and_median_delay():
    s = svc()
    jobs = [s.job(pickup(), ticket(published="2026-07-02T10:00:00Z"), None, "R", 24),
            s.job(pickup(), ticket(published="2026-07-04T10:00:00Z"), None, "R", 24),
            s.job(pickup(), None, None, "R", 24),
            s.job(pickup(), ticket(published=None), None, "R", 24)]
    m = metrics(jobs)
    assert m["tickets_shared_rate"] == 0.5 and m["median_share_lag_days"] == 2.0


def test_weight_difference_uses_single_loads_with_device_weight_only():
    s = svc()
    jobs = [s.job(pickup(dev=1000), ticket(kg=1100), WEIGHED, "R", 24),
            s.job(pickup(dev=1000), ticket(kg=1300), WEIGHED, "R", 24),
            s.job(pickup(dev=1000), ticket(kg=500, loads=2), WEIGHED, "R", 24),
            s.job(pickup(dev=1000), ticket(kg=2000), {"has_weight_measurement": False}, "R", 24)]
    m = metrics(jobs)
    assert m["weight_gap_median_pct"] == 20.0 and m["weight_pairs"] == 2


@lru_cache
def cards():
    _, _, _, scorecard = real_stack()
    return scorecard, scorecard.operators(period="3m")


def test_cards_only_for_operators_this_customer_uses():
    _, res = cards()
    assert res["customer_id"] == "ORG-0001" and [c["operator_id"] for c in res["operators"]] == ["OP-C", "OP-E"]
    for c in res["operators"]:
        assert [m["key"] for m in c["measures"]] == ["on_time", "missed_visits", "tickets_shared", "lines_to_check",
                                                     "weight_vs_ours"]
        assert c["months"] == 3 and c["pickups"] > 0 and c["materials"]


def test_prepare_returns_draft_and_stores_decision():
    scorecard, res = cards()
    card = next(c for c in res["operators"] if c["suggested_action"] != "NONE")
    saved = scorecard.decide(card["operator_id"], "prepare")
    assert saved["draft"].startswith("Hello") and saved["action"] == card["suggested_action"] and saved["created_at"]
    assert scorecard.decide("OP-NOPE", "prepare") is None


@lru_cache
def stack():
    return real_stack()


def lifts(**match):
    comparison = stack()[0]
    return [p for p in comparison.pickups.all() if p["status"] in ("COMPLETED", "PARTIAL")
            and all(p.get(k) == v for k, v in match.items())]


def test_filter_by_customer():
    scorecard = stack()[3]
    res = scorecard.operators(customer_id="ORG-0002")
    assert res["customer_id"] == "ORG-0002" and res["options"]["sites"]
    sites = stack()[3].sites
    assert {s["id"] for s in res["options"]["sites"]} == {s["site_id"] for s in sites.all() if s["customer_id"] == "ORG-0002"}
    for c in res["operators"]:
        assert c["pickups"] == len(lifts(customer_id="ORG-0002", operator_id=c["operator_id"]))


def test_filter_by_site():
    scorecard = stack()[3]
    site = lifts(customer_id="ORG-0001")[0]["site_id"]
    res = scorecard.operators(customer_id="ORG-0001", site_id=site)
    assert res["operators"]
    for c in res["operators"]:
        assert c["pickups"] == len(lifts(site_id=site, operator_id=c["operator_id"]))


def test_filter_by_period_and_months_covered():
    scorecard = stack()[3]
    res = scorecard.operators(start="2026-07", end="2026-07")
    assert res["periods"] == ["2026-07"]
    assert all(c["months_covered"] == ["2026-07"] for c in res["operators"])
    assert scorecard.operators(period="3m")["periods"] == res["options"]["months"][-3:]
    assert scorecard.operators(start="2030-01", end="2030-02")["operators"] == []


def test_all_customers_returns_every_operator_with_pickups():
    scorecard = stack()[3]
    res = scorecard.operators(customer_id="all")
    assert res["customer_name"] == "All customers"
    assert {c["operator_id"] for c in res["operators"]} == {p["operator_id"] for p in lifts()}
    for c in res["operators"]:
        assert c["enough_data"] == (c["pickups"] >= 10)
    assert [c["operator_id"] for c in scorecard.operators(customer_id="all", operator_id="OP-A")["operators"]] == ["OP-A"]
