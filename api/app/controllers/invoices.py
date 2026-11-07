from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.deps import comparison_service
from app.models.schemas import ComparisonResponse, DecisionEntry, DecisionIn, PickupComparison
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("/periods", response_model=list[str])
def get_periods(svc: ComparisonService = Depends(comparison_service)):
    return svc.periods()


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
                   svc: ComparisonService = Depends(comparison_service)):
    return svc.compare(period)


@router.get("/comparison/{pickup_id}", response_model=PickupComparison)
def get_pickup_comparison(pickup_id: str, svc: ComparisonService = Depends(comparison_service)):
    row = svc.detail(pickup_id)
    if row is None:
        raise HTTPException(404, "Pickup not found")
    return row


@router.post("/items/{item_id}/decision", response_model=DecisionEntry)
def post_decision(item_id: str, body: DecisionIn, svc: ComparisonService = Depends(comparison_service)):
    saved = svc.decide(item_id, body.decision)
    if saved is None:
        raise HTTPException(404, "Item not found")
    return saved
