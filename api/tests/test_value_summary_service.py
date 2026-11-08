from cards_check import check_cards, number
from fakes import feature_stack


def test_value_summary_adds_feature_values_and_hypothetical_revenue():
    s = feature_stack()
    res = s["value"].summary()
    c = check_cards(res)["value.summary"]
    guard = s["pickups"].min_charge()
    sizing = s["fleet"].right_size()
    total = sum(x["topup_cents"] for x in guard["could_wait"]) * 12 / guard["months"] + sum(o["saving_cents"] for o in sizing["fits"])
    assert res["value_per_device_cents"] == round(total / res["devices"])
    assert number(c, "Package price per device per year")["tag"] == "HYPOTHETICAL" and c["actions"] == []
    assert len(res["scenarios"]) == 3 * 3
    low = next(x for x in res["scenarios"] if x["price"] == 29 and x["adoption_pct"] == 20)
    assert low["revenue_eur"] == round(res["devices"] * 0.2 * 29 * 12)


def test_value_page_uses_params_and_adds_up():
    from fakes import feature_stack
    params = {"plans": {"weight_eur_per_container_month": 39, "pro_eur_per_container_month": 69},
              "market": {"connected_containers": 500}, "adoption": {"adoption_share_of_eligible_pct": [20, 40]}}
    svc = feature_stack(params)["services"].value
    r = svc.value_page("all")
    assert r["europress"]["yearly_eur"] == 500 * 20 // 100 * 39 * 12 == 46800
    assert r["europress"]["text"] == "If 20 % of 500 connected containers take the Weight plan"
    assert r["plan_cost_cents"] == 39 * 100 * r["devices"] * r["months"]
    assert r["net_cents"] == r["value_found_cents"] - r["plan_cost_cents"]
    assert [p["price_eur"] for p in r["plans"]] == [None, 39, 69] and r["why"]["cost"]["evidence"] == "hypothetical"
