from fastapi import APIRouter, HTTPException, Query

from app.controllers.deps import ScopedServices
from app.models.schemas import DecisionEntry, HistoryEntry
from app.services.registry import Services

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("", response_model=list[HistoryEntry])
def get_decisions(months: int = Query(3, ge=1, le=24), svc: Services = ScopedServices):
    return svc.decisions.history(months)


@router.post("/{decision_id}/undo", response_model=DecisionEntry)
def undo(decision_id: str, svc: Services = ScopedServices):
    saved = svc.decisions.undo(decision_id)
    if saved is None:
        raise HTTPException(404, "Decision not found")
    return saved
