from fastapi import APIRouter, Query

from app.controllers.deps import ScopedServices
from app.models.schemas import CostsResponse
from app.services.registry import Services

router = APIRouter(prefix="/api/costs", tags=["costs"])


@router.get("", response_model=CostsResponse)
def get_costs(months: int = Query(3, ge=1, le=24), period: str | None = Query(None, pattern=r"^(3m|6m|12m|all)$"),
              svc: Services = ScopedServices):
    return svc.costs.costs(months, customer_id=svc.customer_id, period=period)
