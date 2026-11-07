from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.deps import decision_service
from app.models.schemas import DecisionEntry, HistoryEntry
from app.services.decision_service import DecisionService

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("", response_model=list[HistoryEntry])
def get_decisions(months: int = Query(3, ge=1, le=24), svc: DecisionService = Depends(decision_service)):
    return svc.history(months)


@router.post("/{decision_id}/undo", response_model=DecisionEntry)
def undo(decision_id: str, svc: DecisionService = Depends(decision_service)):
    saved = svc.undo(decision_id)
    if saved is None:
        raise HTTPException(404, "Decision not found")
    return saved
