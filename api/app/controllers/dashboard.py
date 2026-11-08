from fastapi import APIRouter, Depends, Query

from app.controllers.deps import ScopedServices, unscoped
from app.models.schemas import DashboardResponse, Option
from app.services.registry import Services

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(period: str | None = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"), svc: Services = ScopedServices):
    return svc.dashboard.dashboard(svc.customer_id, period)


@router.get("/demo/customers", response_model=list[Option])
def demo_customers(svc: Services = Depends(unscoped)):
    return svc.dashboard.customers()
