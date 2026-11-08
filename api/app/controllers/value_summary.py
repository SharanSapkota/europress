from fastapi import APIRouter

from app.controllers.deps import ScopedServices
from app.models.schemas import CardsResponse, ValueResponse
from app.services.registry import Services

router = APIRouter(prefix="/api/value-summary", tags=["value_summary"])


@router.get("", response_model=CardsResponse)
def get_summary(svc: Services = ScopedServices):
    return svc.value.summary(svc.customer_id)


value_router = APIRouter(prefix="/api/value", tags=["value"])


@value_router.get("", response_model=ValueResponse)
def get_value(svc: Services = ScopedServices):
    return svc.value.value_page(svc.customer_id)
