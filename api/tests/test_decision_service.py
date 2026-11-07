from fakes import decisions


def record(svc, item, decision, action="REQUEST_TICKETS"):
    return svc.record("operator", item, decision, "Hauler", {"action": action, "text": "Why."}, {"on_time": "75%"})


def test_entry_keeps_suggestion_numbers_user_and_time():
    svc = decisions()
    e = record(svc, "OP-C", "prepare")
    assert e["user"] == "demo user" and e["created_at"] and e["suggestion"]["action"] == "REQUEST_TICKETS"
    assert e["numbers"] == {"on_time": "75%"} and e["item_type"] == "operator"
    assert svc.current("operator", ["OP-C"])["OP-C"]["decision_id"] == e["decision_id"]


def test_undo_adds_an_entry_and_restores_the_previous_decision():
    svc = decisions()
    first = record(svc, "OP-C", "prepare")
    second = record(svc, "OP-C", "not_now")
    undo = svc.undo(second["decision_id"])
    assert undo["decision"] == "undo" and undo["undoes"] == second["decision_id"]
    assert len(svc.repo.entries) == 3
    assert svc.current("operator", ["OP-C"])["OP-C"]["decision_id"] == first["decision_id"]
    assert svc.undo(undo["decision_id"]) is None and svc.undo("nope") is None


def test_history_is_newest_first_and_marks_undone():
    svc = decisions()
    a = record(svc, "OP-C", "not_now", action="RENEGOTIATE")
    assert svc.declined("operator", "OP-C", "RENEGOTIATE")
    svc.undo(a["decision_id"])
    assert not svc.declined("operator", "OP-C", "RENEGOTIATE")
    h = svc.history(3)
    assert [x["decision"] for x in h] == ["undo", "not_now"] and h[1]["undone"] and h[1]["text"] == "Not now"
