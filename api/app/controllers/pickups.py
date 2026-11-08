from fastapi import APIRouter, HTTPException

from app.controllers.deps import ScopedServices
from app.models.schemas import CardsResponse, DecisionEntry, FeatureDecisionIn
from app.services.registry import Services

router = APIRouter(prefix="/api/pickups", tags=["pickups"])


@router.get("", response_model=CardsResponse)
def get_cards(svc: Services = ScopedServices):
    return svc.pickups.cards(svc.customer_id)


@router.post("/{card_id}/decision", response_model=DecisionEntry)
def post_decision(card_id: str, body: FeatureDecisionIn, svc: Services = ScopedServices):
    saved = svc.pickups.decide(card_id, body.decision, svc.customer_id)
    if saved is None:
        raise HTTPException(404, "Feature not found")
    return saved
