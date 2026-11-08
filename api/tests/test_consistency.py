from fakes import real_stack


def test_operator_check_lines_equal_invoice_check_items():
    comparison, _, _, scorecard = real_stack()
    cards = {c["operator_id"]: c for c in scorecard.operators(period="3m")["operators"]}
    periods = comparison.periods()[-3:]
    facts = scorecard._facts(comparison.customer_id(None), periods, 2)
    counted = {}
    for p in periods:
        res = comparison.compare(p)
        for r in res["rows"]:
            if r["found_status"] == "CHECK":
                ids = {i["entity_id"] for i in r["items"] if i["status"] == "CHECK" and i["entity_type"] == "invoice_line"}
                counted[r["operator_id"]] = counted.get(r["operator_id"], 0) + len(ids)
        for u in res["unmatched_lines"]:
            if u["status"] == "CHECK":
                counted[u["operator_id"]] = counted.get(u["operator_id"], 0) + 1
    for op in cards:
        m = scorecard.metrics(*[[x for x in facts[k] if x["key"][0] == op] for k in ("jobs", "lines", "missing")])
        assert m["lines_to_check"] == counted.get(op, 0), op


def test_cost_pickups_equal_invoice_pickups_per_container():
    comparison, costs, _, _ = real_stack()
    res = costs.costs(3)
    lifts = {}
    for p in res["periods"]:
        for r in comparison.compare(p)["rows"]:
            if r["pickup_status"] in ("COMPLETED", "PARTIAL"):
                lifts.setdefault(r["device_id"], set()).add(r["pickup_id"])
    for c in res["containers"]:
        assert c["pickups"] == len(lifts.get(c["device_id"], set())), c["device_id"]
