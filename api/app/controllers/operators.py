from fastapi import APIRouter, Depends, HTTPException, Query

from app.controllers.deps import scorecard_service
from app.models.schemas import OperatorDecisionIn, OperatorDecisionOut, OperatorsResponse
from app.services.scorecard_service import ScorecardService

router = APIRouter(prefix="/api/operators", tags=["operators"])
MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


def filters(customer_id: str | None = None, site_id: str | None = None,
            period: str = Query("all", pattern=r"^(3m|6m|12m|all)$"),
            start: str | None = Query(None, alias="from", pattern=MONTH),
            end: str | None = Query(None, alias="to", pattern=MONTH)) -> dict:
    return {"customer_id": customer_id or None, "site_id": site_id or None, "period": period, "start": start, "end": end}


@router.get("", response_model=OperatorsResponse, response_model_by_alias=True)
def get_operators(f: dict = Depends(filters), operator_id: str | None = None,
                  svc: ScorecardService = Depends(scorecard_service)):
    return svc.operators(**f, operator_id=operator_id or None)


@router.post("/{operator_id}/decision", response_model=OperatorDecisionOut)
def post_decision(operator_id: str, body: OperatorDecisionIn, f: dict = Depends(filters),
                  svc: ScorecardService = Depends(scorecard_service)):
    saved = svc.decide(operator_id, body.decision, **f)
    if saved is None:
        raise HTTPException(404, "No suggested action for this operator")
    return saved
