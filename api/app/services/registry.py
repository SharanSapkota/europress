from functools import cached_property

from app.core.config import Settings
from app.services.comparison_service import ComparisonService
from app.services.cost_service import CostService
from app.services.containers_service import ContainersService
from app.services.dashboard_service import DashboardService
from app.services.decision_service import DecisionService
from app.services.feature_data import FeatureData
from app.services.fleet_service import FleetService
from app.services.operator_action_service import OperatorActionService
from app.services.our_invoice_service import OurInvoiceService
from app.services.pickups_service import PickupsService
from app.services.scorecard_service import ScorecardService
from app.services.site_checks_service import SiteChecksService
from app.services.suggestion_service import SuggestionService
from app.services.value_summary_service import ValueSummaryService


class Services:
    def __init__(self, repos: dict, settings: Settings, params: dict, customer_id: str | None = None,
                 site_id: str | None = None, peers: bool = True):
        self.r = repos
        self.s = settings
        self.params = params
        self.customer_id = customer_id
        self.site_id = site_id
        self.peers = peers

    @property
    def scope(self) -> str:
        return self.customer_id or "all"

    @cached_property
    def decisions(self) -> DecisionService:
        return DecisionService(self.r["decisions"], self.s, self.customer_id)

    @cached_property
    def comparison(self) -> ComparisonService:
        r = self.r
        ours = OurInvoiceService(r["devices"], r["tickets"], r["quality"], r["contracts"], r["versions"],
                                 r["price_index"], r["materials"], self.s)
        return ComparisonService(r["pickups"], r["invoices"], r["lines"], self.decisions, ours, self.s,
                                 r["customers"], r["sites"], r["operators"])

    @cached_property
    def costs(self) -> CostService:
        return CostService(self.comparison, self.r["devices"], self.r["sites"], self.s, self.r["daily"])

    @cached_property
    def actions(self) -> OperatorActionService | None:
        if not self.peers:
            return None
        r = self.r
        return OperatorActionService(self.comparison, r["contracts"], r["versions"], r["devices"], r["sites"],
                                     r["materials"], r["operators"], r["tickets"], self.s)

    @cached_property
    def scorecard(self) -> ScorecardService:
        r = self.r
        return ScorecardService(self.comparison, self.actions, SuggestionService(self.s), r["pickups"], r["tickets"],
                                r["devices"], r["sites"], r["contracts"], r["operators"], self.decisions, self.s)

    @cached_property
    def data(self) -> FeatureData:
        r = self.r
        return FeatureData(self.comparison, r["pickups"], r["tickets"], r["devices"], r["sites"], r["contracts"],
                           r["materials"], r["quality"], r["grade_rules"], r["work_orders"], r["calendar"], r["daily"],
                           r["price_index"])

    @cached_property
    def pickups(self) -> PickupsService:
        return PickupsService(self.data, self.decisions, self.s)

    @cached_property
    def containers(self) -> ContainersService:
        return ContainersService(self.data, self.pickups, self.decisions, self.s)

    @cached_property
    def site_checks(self) -> SiteChecksService:
        return SiteChecksService(self.data, self.decisions)

    @cached_property
    def fleet(self) -> FleetService:
        return FleetService(self.data, self.decisions, self.params)

    @cached_property
    def value(self) -> ValueSummaryService:
        return ValueSummaryService(self.data, self.pickups, self.fleet, self.params, self.comparison)

    @cached_property
    def dashboard(self) -> DashboardService:
        return DashboardService(self.comparison, self.costs, self.pickups, self.fleet, self.data, self.s,
                                self.r.get("customer_sites"))
