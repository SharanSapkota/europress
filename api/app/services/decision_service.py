import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings

DECISION_TEXT = {"ok": "Marked as OK", "dispute_draft": "Question prepared", "dispute_sent": "Question sent",
                 "prepare": "Request prepared", "not_now": "Not now", "undo": "Undone"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class DecisionService:
    def __init__(self, repo, settings: Settings):
        self.repo = repo
        self.s = settings

    def record(self, item_type: str, item_id: str, decision: str, label: str, suggestion: dict,
               numbers: dict, undoes: str | None = None) -> dict:
        entry = {"_id": str(uuid.uuid4()), "item_type": item_type, "item_id": item_id, "label": label,
                 "decision": decision, "suggestion": suggestion, "numbers": numbers, "undoes": undoes,
                 "created_at": now(), "user": self.s.user}
        entry["decision_id"] = entry["_id"]
        return self._out(self.repo.add(entry))

    @staticmethod
    def _out(e: dict) -> dict:
        return {k: v for k, v in e.items() if k != "_id"}

    def effective(self, entries: list[dict]) -> list[dict]:
        undone = {e["undoes"] for e in entries if e["decision"] == "undo"}
        return [e for e in entries if e["decision"] != "undo" and e["decision_id"] not in undone]

    def current(self, item_type: str, item_ids: list[str]) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for e in self.effective(self.repo.for_items(item_type, item_ids)):
            out[e["item_id"]] = self._out(e)
        return out

    def declined(self, item_type: str, item_id: str, action: str) -> bool:
        return any(e["decision"] == "not_now" and (e.get("suggestion") or {}).get("action") == action
                   for e in self.effective(self.repo.for_items(item_type, [item_id])))

    def history(self, months: int = 3) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=round(months * 30.4375))).strftime("%Y-%m-%dT%H:%M:%S")
        entries = self.repo.since(since)
        undone = {e["undoes"] for e in entries if e["decision"] == "undo"}
        return [dict(self._out(e), text=DECISION_TEXT.get(e["decision"], e["decision"]),
                     undone=e["decision_id"] in undone) for e in entries]

    def undo(self, decision_id: str) -> dict | None:
        old = self.repo.get(decision_id)
        if not old or old["decision"] == "undo":
            return None
        return self.record(old["item_type"], old["item_id"], "undo", old["label"], old["suggestion"],
                           old["numbers"], undoes=decision_id)
