from fastapi import APIRouter, HTTPException

from app.controllers.deps import ScopedServices
from app.models.schemas import ContainerDecisionIn, ContainersResponse, DecisionEntry
from app.services.registry import Services

router = APIRouter(prefix="/api/containers", tags=["containers"])


@router.get("", response_model=ContainersResponse)
def get_containers(svc: Services = ScopedServices):
    return svc.containers.cards(svc.customer_id)


@router.post("/{card_id}/decision", response_model=DecisionEntry)
def post_decision(card_id: str, body: ContainerDecisionIn, svc: Services = ScopedServices):
    saved = svc.containers.decide(card_id, body.decision, svc.customer_id)
    if saved is None:
        raise HTTPException(404, "Suggestion not found")
    return saved
