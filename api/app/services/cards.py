DRAFT_NOTE = "Draft only. Nothing is sent without your approval."
LEVEL = {"high": "High", "medium": "Medium", "low": "Low"}
SEVERITY = {"Check this": 0, "Worth a check": 1, "Good": 2, "Not enough data": 3}


def fig(label: str, value, unit: str = "", tag: str = "ESTIMATED", range_: str | None = None) -> dict:
    return {"label": label, "value": value, "unit": unit, "tag": tag, "range": range_}


def bar(label: str, value: float, unit: str, tag: str) -> dict:
    return {"label": label, "value": round(value, 1), "unit": unit, "tag": tag}


def confidence(n: int) -> str:
    return "High" if n >= 30 else ("Medium" if n >= 10 else "Low")


def card(card_id: str, title: str, subtitle: str, status: str, explanation: str, reasoning: tuple[str, str, str],
         example: dict | None, evidence: dict, advanced: dict, actions: bool = True) -> dict:
    return {
        "id": card_id, "title": title, "subtitle": subtitle, "status": status, "explanation": explanation,
        "reasoning": [{"title": t, "text": x} for t, x in zip(("What fill % misses", "What weight shows", "What you gain"),
                                                             reasoning)],
        "example": example, "evidence": {**evidence, "draft_note": DRAFT_NOTE},
        "actions": ["prepare", "not_now", "undo"] if actions else [], "advanced": advanced,
        "decision": None, "decision_id": None, "decided_at": None,
        "headline": title, "example_line": "", "value_cents": 0, "rank": SEVERITY.get(status, 3),
    }


def finish(c: dict, headline: str, example_line: str, value_cents: float = 0) -> dict:
    c.update(headline=headline, example_line=example_line, value_cents=round(value_cents),
             rank=SEVERITY.get(c["status"], 3) * 10 ** 9 - round(abs(value_cents)))
    return c


def example(site: str | None, device: str | None, numbers: list[dict], bars: list[dict], result: str) -> dict:
    return {"site": site, "device": device, "numbers": numbers, "bars": bars, "result": result}


def evidence(tag: str, range_: str | None, n: int, data_used: str, neutrality: str) -> dict:
    return {"tag": tag, "range": range_, "confidence": confidence(n), "pickups_used": n, "data_used": data_used,
            "neutrality_note": neutrality}


def advanced(formula: str, columns: list[str], rows: list[list]) -> dict:
    return {"formula": formula, "columns": columns, "rows": rows}


def kg(value: float) -> str:
    return f"{round(value):,} kg".replace(",", "\u00a0")


def tonnes(kg: float | None) -> str:
    return "–" if kg is None else f"{kg / 1000:.1f}".replace(".", ",")


def days(n: float) -> str:
    n = round(n)
    return f"{n} {'day' if n == 1 else 'days'}"


def whole(value: float) -> str:
    return f"{round(value):,}".replace(",", "\u00a0")


def row(date: str | None, label: str, value: float | None, unit: str, bar_value: float | None = None,
        bar_max: float | None = None, bar_text: str = "", note: str = "", tone: str = "muted") -> dict:
    bar = {"value": max(0.0, bar_value), "max": max(bar_max, bar_value, 1e-9)} if bar_value is not None and bar_max else None
    return {"date": (date or "")[:10] or None, "label": label, "bar": bar, "bar_text": bar_text, "note": note,
            "tone": tone, "value": None if value is None else round(value), "unit": unit}


def details(summary: str, info: str, columns: list[str], rows: list[dict]) -> dict:
    return {"summary": summary, "info": info, "columns": columns, "rows": rows}


def eur(cents: float) -> str:
    return f"{round(cents) / 100:,.0f} €".replace(",", " ")
