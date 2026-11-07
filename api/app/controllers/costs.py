from fastapi import APIRouter, Depends, Query

from app.controllers.deps import cost_service
from app.models.schemas import CostsResponse
from app.services.cost_service import CostService

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("", response_model=CostsResponse)
def get_costs(months: int = Query(3, ge=1, le=24), period: str | None = Query(None, pattern=r"^(3m|6m|12m|all)$"),
              svc: CostService = Depends(cost_service)):
    return svc.costs(months, period=period)
