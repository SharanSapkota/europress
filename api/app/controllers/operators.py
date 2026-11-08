from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.deps import ScopedServices
from app.models.schemas import OperatorDecisionIn, OperatorDecisionOut, OperatorsResponse
from app.services.registry import Services

router = APIRouter(prefix="/api/operators", tags=["operators"])
MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


def filters(period: str = Query("all", pattern=r"^(3m|6m|12m|all)$"),
            start: str | None = Query(None, alias="from", pattern=MONTH),
            end: str | None = Query(None, alias="to", pattern=MONTH)) -> dict:
    return {"period": period, "start": start, "end": end}


@router.get("", response_model=OperatorsResponse, response_model_by_alias=True)
def get_operators(f: dict = Depends(filters), operator_id: str | None = None, svc: Services = ScopedServices):
    return svc.scorecard.operators(customer_id=svc.customer_id, site_id=svc.site_id, operator_id=operator_id or None, **f)


@router.post("/{operator_id}/decision", response_model=OperatorDecisionOut)
def post_decision(operator_id: str, body: OperatorDecisionIn, f: dict = Depends(filters), svc: Services = ScopedServices):
    saved = svc.scorecard.decide(operator_id, body.decision, body.message, customer_id=svc.customer_id,
                                 site_id=svc.site_id, **f)
    if saved is None:
        raise HTTPException(404, "No suggested action for this operator")
    return saved
