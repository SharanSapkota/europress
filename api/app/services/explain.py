LEVELS = {"high": "high", "medium": "low", "low": "low", "not enough data": "not enough data"}
EVIDENCE = ("observed", "estimated", "simulated", "hypothetical")


def level(confidence: str | None) -> str:
    return LEVELS.get((confidence or "not enough data").lower(), "low")


def why(what: str, source: str | None, confidence: str | None, reason: str | None = None,
        evidence: str = "estimated") -> dict:
    return {"what": what, "source": source or "Not enough data", "confidence": level(confidence), "reason": reason,
            "evidence": evidence}


def listing(ids: list[str], noun: str, limit: int = 3) -> str:
    ids = sorted({i for i in ids if i})
    if not ids:
        return ""
    head = ", ".join(ids[:limit])
    more = f" and {len(ids) - limit} more" if len(ids) > limit else ""
    return f"{noun} {head}{more}"
