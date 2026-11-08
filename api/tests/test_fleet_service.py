from functools import lru_cache

from cards_check import check_cards, number
from fakes import feature_stack


@lru_cache
def cards(lease=15):
    params = {"equipment": {"lease_per_m3_month_eur": lease}}
    return check_cards(feature_stack(params)["fleet"].cards())


def test_tare_check_best_example():
    c = cards()["fleet.tare"]
    assert c["status"] == "Check this" and number(c, "Truck")["value"] == "OP-B-V04"
    assert number(c, "Difference")["value"] == "+450" and number(c, "Difference")["tag"] == "OBSERVED"
    assert "41 trucks" in c["reasoning"][1]["text"] and "12 differ" in c["reasoning"][1]["text"]
    assert sum(1 for r in c["advanced"]["rows"] if r[0] == "Our scale was serviced") == 9


def test_right_sizing_subtracts_hypothetical_lease():
    c = cards()["fleet.right_size"]
    assert c["example"]["device"] == "CMP-00001" and number(c, "Suggested size")["value"] == "10 m³"
    assert number(c, "Pickups avoided per year")["value"] == 12
    assert number(c, "Pickup fees avoided per year")["value"] == 2746
    lease = number(c, "Extra lease per year")
    assert lease["value"] == 360 and lease["tag"] == "HYPOTHETICAL"
    assert number(c, "Net saving per year")["value"] == 2386
    assert number(cards(0)["fleet.right_size"], "Net saving per year")["value"] == 2746
