import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import Settings

DECISION_TEXT = {"ok": "Marked as OK", "dispute_draft": "Question prepared", "dispute_sent": "Disputed",
                 "question": "Disputed", "prepare": "Request prepared", "approve": "Approved", "not_now": "Not now",
                 "undo": "Undone"}
CHIP_TONE = {"ok": "neutral", "dispute_draft": "blue", "dispute_sent": "disputed", "question": "disputed",
             "prepare": "blue", "approve": "good", "not_now": "neutral", "undo": "neutral"}
ACTION_TEXT = {"CORRECT_LINE": "Submit a dispute", "REQUEST_TICKET": "Ask for the scale ticket", "NONE": "No action",
               "REQUEST_TICKETS": "Ask for missing scale tickets", "CORRECT_LINES": "Ask to correct the billed lifts",
               "RENEGOTIATE": "Renegotiate the contract", "TENDER": "Ask other operators for offers",
               "PREPARE_PROPOSAL": "Prepare the change"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class DecisionService:
    def __init__(self, repo, settings: Settings, customer_id: str | None = None):
        self.repo = repo
        self.s = settings
        self.customer_id = customer_id

    def record(self, item_type: str, item_id: str, decision: str, label: str, suggestion: dict,
               numbers: dict, undoes: str | None = None, evidence: dict | None = None, message: str | None = None,
               view: dict | None = None) -> dict:
        entry = {"_id": str(uuid.uuid4()), "item_type": item_type, "item_id": item_id, "label": label,
                 "decision": decision, "suggestion": suggestion, "numbers": numbers, "undoes": undoes,
                 "evidence": evidence, "message": message, "view": view,
                 "created_at": now(), "user": self.s.user, "customer_id": self.customer_id}
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
        return [dict(self._out(e), **self.present(e), text=DECISION_TEXT.get(e["decision"], e["decision"]),
                     undone=e["decision_id"] in undone) for e in entries]

    @staticmethod
    def present(e: dict) -> dict:
        view = e.get("view") or {}
        sug = e.get("suggestion") or {}
        text = (sug.get("text") or "").split(". ")[0].rstrip(".")
        return {"title": view.get("title") or e["label"],
                "detail": view.get("detail") if view.get("detail") is not None else text,
                "suggestion_text": view.get("suggestion") or ACTION_TEXT.get(sug.get("action") or "", "No action"),
                "chip": DECISION_TEXT.get(e["decision"], e["decision"]),
                "chip_tone": CHIP_TONE.get(e["decision"], "neutral"),
                "trail": view.get("trail") or []}

    def undo(self, decision_id: str) -> dict | None:
        old = self.repo.get(decision_id)
        if not old or old["decision"] == "undo":
            return None
        return self.record(old["item_type"], old["item_id"], "undo", old["label"], old["suggestion"],
                           old["numbers"], undoes=decision_id, evidence=old.get("evidence"), view=old.get("view"))
