from fastapi import APIRouter, Depends, HTTPException

from app.controllers.deps import weight_ideas_service
from app.models.schemas import IdeaDecisionIn, IdeaDecisionOut, PrimaryIdeasResponse, SecondaryIdeasResponse
from app.services.weight_ideas_service import WeightIdeasService

router = APIRouter(prefix="/api/weight-ideas", tags=["weight-ideas"])


@router.get("/primary", response_model=PrimaryIdeasResponse)
def get_primary(customer_id: str | None = "all", svc: WeightIdeasService = Depends(weight_ideas_service)):
    return svc.primary_ideas(customer_id)


@router.get("/secondary", response_model=SecondaryIdeasResponse)
def get_secondary(customer_id: str | None = "all", svc: WeightIdeasService = Depends(weight_ideas_service)):
    return svc.secondary_ideas(customer_id)


@router.post("/{item_id}/decision", response_model=IdeaDecisionOut)
def post_decision(item_id: str, body: IdeaDecisionIn, customer_id: str | None = "all",
                  svc: WeightIdeasService = Depends(weight_ideas_service)):
    saved = svc.decide(item_id, body.decision, customer_id)
    if saved is None:
        raise HTTPException(404, "Weight idea item not found")
    return saved
