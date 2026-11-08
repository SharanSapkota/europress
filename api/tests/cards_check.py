from app.models.schemas import CardsResponse

BANNED = ("balex", "penalty", "certified", "overcharge", "fraud", "error", "kg of cardboard")


def check_cards(res: dict) -> dict:
    out = CardsResponse(**res).model_dump()
    for c in out["cards"]:
        assert len(c["headline"]) < 90 and any(ch.isdigit() for ch in c["headline"]), c["headline"]
        assert c["example_line"] or not c["example"]
        det = c["details"]
        assert det["summary"] and det["info"] and len(det["columns"]) == 4
        assert all("COL-" not in r["label"] and "ORG-" not in r["label"] for r in det["rows"])
        assert len(c["reasoning"]) == 3 and c["evidence"]["draft_note"] and c["evidence"]["neutrality_note"]
        assert len(c["actions"]) <= 3
        if c["example"]:
            assert len(c["example"]["bars"]) == 2
            assert all(n["tag"] for n in c["example"]["numbers"])
        text = str(c).lower()
        assert not any(w in text for w in BANNED), c["id"]
    return {c["id"]: c for c in out["cards"]}


def number(card: dict, label: str):
    return next(n for n in card["example"]["numbers"] if n["label"] == label)
