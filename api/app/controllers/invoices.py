from fastapi import APIRouter, HTTPException, Query

from app.controllers.deps import ScopedServices
from app.models.schemas import ComparisonResponse, DecisionEntry, DecisionIn, PickupComparison
from app.services.registry import Services

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("/periods", response_model=list[str])
def get_periods(svc: Services = ScopedServices):
    return svc.comparison.periods()


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(period: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), svc: Services = ScopedServices):
    return svc.comparison.compare(period, svc.customer_id)


@router.get("/comparison/{pickup_id}", response_model=PickupComparison)
def get_pickup_comparison(pickup_id: str, svc: Services = ScopedServices):
    row = svc.comparison.detail(pickup_id)
    if row is None:
        raise HTTPException(404, "Pickup not found")
    return row


@router.post("/items/{item_id}/decision", response_model=DecisionEntry)
def post_decision(item_id: str, body: DecisionIn, svc: Services = ScopedServices):
    saved = svc.comparison.decide(item_id, body.decision, body.message)
    if saved is None:
        raise HTTPException(404, "Item not found")
    return saved


@router.post("/comparison/{pickup_id}/decision", response_model=DecisionEntry)
def post_pickup_decision(pickup_id: str, body: DecisionIn, svc: Services = ScopedServices):
    return post_decision(pickup_id, body, svc)
