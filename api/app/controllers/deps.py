from app.core.config import settings
from app.core.db import get_db
from app.repositories import mongo as r
from app.services.comparison_service import ComparisonService
from app.services.cost_service import CostService
from app.services.decision_service import DecisionService
from app.services.operator_action_service import OperatorActionService
from app.services.our_invoice_service import OurInvoiceService
from app.services.scorecard_service import ScorecardService
from app.services.suggestion_service import SuggestionService
from app.services.weight_ideas_service import WeightIdeasService


def decision_service() -> DecisionService:
    return DecisionService(r.DecisionRepository(get_db()), settings)


def comparison_service() -> ComparisonService:
    db = get_db()
    ours = OurInvoiceService(r.DeviceRepository(db), r.TicketRepository(db), r.QualityRepository(db),
                             r.ContractRepository(db), r.ContractVersionRepository(db), r.PriceIndexRepository(db),
                             r.MaterialRepository(db), settings)
    return ComparisonService(r.PickupRepository(db), r.OperatorInvoiceRepository(db),
                             r.OperatorInvoiceLineRepository(db), decision_service(), ours, settings,
                             r.CustomerRepository(db), r.SiteRepository(db), r.OperatorRepository(db))


def cost_service() -> CostService:
    db = get_db()
    return CostService(comparison_service(), r.DeviceRepository(db), r.SiteRepository(db), settings,
                       r.TelemetryDailyRepository(db))


def action_service(comparison: ComparisonService | None = None) -> OperatorActionService:
    db = get_db()
    return OperatorActionService(comparison or comparison_service(), r.ContractRepository(db),
                                 r.ContractVersionRepository(db), r.DeviceRepository(db), r.SiteRepository(db),
                                 r.MaterialRepository(db), r.OperatorRepository(db), r.TicketRepository(db), settings)


def scorecard_service() -> ScorecardService:
    db = get_db()
    comparison = comparison_service()
    return ScorecardService(comparison, action_service(comparison), SuggestionService(settings), r.PickupRepository(db),
                            r.TicketRepository(db), r.DeviceRepository(db), r.SiteRepository(db), r.ContractRepository(db),
                            r.OperatorRepository(db), comparison.decisions, settings)


def weight_ideas_service() -> WeightIdeasService:
    db = get_db()
    comparison = comparison_service()
    return WeightIdeasService(comparison, r.PickupRepository(db), r.TicketRepository(db), r.DeviceRepository(db),
                              r.SiteRepository(db), r.ContractRepository(db), r.ContractVersionRepository(db),
                              r.MaterialRepository(db), r.MaintenanceRepository(db), r.DecisionCaseRepository(db),
                              comparison.decisions, settings)
