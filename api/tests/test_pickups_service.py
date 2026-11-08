from functools import lru_cache

from cards_check import check_cards, number
from fakes import feature_stack


@lru_cache
def stack():
    return feature_stack()


def test_min_charge_guard_best_example():
    res = stack()["pickups"].min_charge()
    assert len(res["topups"]) == 91 and len(res["could_wait"]) == 23
    assert round(sum(t["topup_cents"] for t in res["topups"]) / 100) == 7636
    c = check_cards({"customer_id": "all", "cards": [res["card"]]})["pickups.min_charge_guard"]
    assert c["status"] == "Check this" and number(c, "Pickup")["value"] == "COL-00026-0006"
    assert number(c, "Weight at pickup")["value"] == 220 and number(c, "Break-even weight")["value"] == 1159
    assert number(c, "Minimum charge top-up")["value"] == 158.71 and number(c, "Minimum charge top-up")["tag"] == "OBSERVED"
    assert number(c, "More days it could wait")["value"] == 4.3 and number(c, "Days allowed between pickups")["value"] == 21


def test_day0_receipt_is_provisional_with_a_range():
    res = stack()["pickups"].day0()
    c = check_cards({"customer_id": "all", "cards": [res["card"]]})["pickups.day0_receipt"]
    assert number(c, "Pickup")["value"] == "COL-00020-0003" and number(c, "Weight at pickup")["value"] == 3100
    credit = number(c, "Expected credit")
    assert credit["value"] == 175 and credit["tag"] == "ESTIMATED" and "–" in credit["range"]
    assert round(res["spread"], 2) == 0.18 and number(c, "Final credit")["value"] == 114
    assert c["title"] == "Provisional pickup receipt"


def test_prepare_and_undo_are_stored():
    s = stack()
    saved = s["pickups"].decide("pickups.min_charge_guard", "prepare")
    assert saved["item_type"] == "feature" and saved["numbers"]["Pickup"] == "COL-00026-0006"
    card = s["pickups"].cards()["cards"][0]
    assert card["decision"] == "prepare" and card["decision_id"] == saved["decision_id"]
    s["decisions"].undo(saved["decision_id"])
    assert s["pickups"].cards()["cards"][0]["decision"] is None
    assert s["pickups"].decide("pickups.nope", "prepare") is None
