from functools import lru_cache

from cards_check import check_cards, number
from fakes import feature_stack


@lru_cache
def cards():
    return check_cards(feature_stack()["site_checks"].cards())


def test_left_in_container_best_example():
    c = cards()["site_checks.left_in_container"]
    assert number(c, "Pickup")["value"] == "COL-00024-0050"
    assert number(c, "Weight before pickup")["value"] == 2720 and number(c, "Weight after pickup")["value"] == 710
    assert number(c, "Share left")["value"] == 26 and c["evidence"]["pickups_used"] == 17


def test_shared_split_moves_cost_between_own_sites():
    c = cards()["site_checks.shared_split"]
    assert number(c, "Shared weighing")["value"] == "WB-OP-A-00034-0009"
    values = [n["value"] for n in c["example"]["numbers"]]
    assert "+2368 kg (+273 €)" in values and "-2368 kg (-300 €)" in values
    assert number(c, "Net difference from different contract rates")["value"] == -27
    assert c["evidence"]["neutrality_note"] == "This is about your own sites' cost split, not an operator mistake."


def test_density_check_never_claims_savings():
    c = cards()["site_checks.density"]
    assert c["example"]["device"] == "CMP-00026" and c["status"] == "Worth a check"
    assert number(c, "Density at pickup (median)")["value"] == 289 and number(c, "Compared with normal")["value"] == 76
    assert c["example"]["result"].startswith("Lighter than normal. This often means light packaging")
    assert "€" not in str(c["example"]) and "No saving is claimed" in c["evidence"]["neutrality_note"]
