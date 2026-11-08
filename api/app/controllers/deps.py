from fastapi import Depends, HTTPException

from app.core.config import settings
from app.core.db import get_db
from app.core.params import params
from app.repositories import mongo as r
from app.repositories.scope import Scope, scope_repos
from app.services.registry import Services


def base_repos(db) -> dict:
    return {
        "devices": r.DeviceRepository(db), "sites": r.SiteRepository(db), "contracts": r.ContractRepository(db),
        "pickups": r.PickupRepository(db), "invoices": r.OperatorInvoiceRepository(db),
        "lines": r.OperatorInvoiceLineRepository(db), "versions": r.ContractVersionRepository(db),
        "tickets": r.TicketRepository(db), "quality": r.QualityRepository(db), "daily": r.TelemetryDailyRepository(db),
        "telemetry": r.TelemetryRepository(db), "work_orders": r.WorkOrderRepository(db),
        "calendar": r.SiteCalendarRepository(db), "operators": r.OperatorRepository(db),
        "customers": r.CustomerRepository(db), "decisions": r.DecisionRepository(db),
        "price_index": r.PriceIndexRepository(db), "materials": r.MaterialRepository(db),
        "grade_rules": r.GradeRuleRepository(db),
    }


def resolve_scope(customer_id: str | None, site_id: str | None, base: dict) -> Scope:
    customers = [c["customer_id"] for c in base["customers"].all()]
    cid = customer_id or settings.customer_id or (customers[0] if customers else None)
    if cid not in customers:
        raise HTTPException(404, "Customer not found")
    if site_id and (base["sites"].get(site_id) or {}).get("customer_id") != cid:
        raise HTTPException(404, "Site not found")
    return Scope(cid, site_id or None)


def services(customer_id: str | None = None, site_id: str | None = None) -> Services:
    base = base_repos(get_db())
    scope = resolve_scope(customer_id, site_id, base)
    return Services(scope_repos(base, scope), settings, params(), scope.customer_id, scope.site_id, peers=False)


def unscoped() -> Services:
    return Services(base_repos(get_db()), settings, params())


ScopedServices = Depends(services)
