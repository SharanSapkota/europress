import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from app.repositories import mongo  # noqa: E402
from seed import read_csv  # noqa: E402

CSV_DIR = ROOT.parent / "data" / "quickstart" / "public" / "csv"


class FakeRepo:
    def __init__(self, docs: list[dict] | None = None):
        self.docs = {d["_id"]: d for d in (docs or [])}

    def get(self, _id):
        return self.docs.get(_id)

    def all(self):
        return list(self.docs.values())

    def _find(self, **kv):
        return [d for d in self.docs.values() if all(d.get(k) == v for k, v in kv.items())]

    def by_job_ref(self, ref):
        return next(iter(self._find(operator_job_ref=ref)), None)

    def by_ticket(self, ticket_id):
        return next(iter(self._find(ticket_id=ticket_id)), None)

    def for_contract(self, contract_id):
        return sorted(self._find(contract_id=contract_id), key=lambda d: d["version_no"])

    def price(self, index_id, month):
        return next(iter(self._find(index_id=index_id, month=month)), None)

    def periods(self):
        return sorted({d["billing_period"] for d in self.docs.values()})

    def by_period(self, period):
        return self._find(billing_period=period)

    def by_invoices(self, ids):
        return sorted([d for d in self.docs.values() if d["invoice_id"] in ids], key=lambda d: (d["invoice_id"], d["line_no"]))

    def save(self, pickup_id, decision, user):
        self.docs[pickup_id] = {"_id": pickup_id, "pickup_id": pickup_id, "decision": decision, "user": user,
                                "decided_at": "2026-10-01T08:00:00Z"}
        return self.docs[pickup_id]

    def for_devices(self, ids, start_month, end_month):
        return [d for d in self.docs.values() if d["device_id"] in ids and start_month <= d["date"][:7] <= end_month]

    def by_pickups(self, ids):
        return {k: v for k, v in self.docs.items() if k in ids}


KEYS = {c.name: c.key for c in vars(mongo).values() if isinstance(c, type) and issubclass(c, mongo._Repo)}


def load(name: str) -> FakeRepo:
    docs = [mongo.to_domain(d) for d in read_csv(CSV_DIR / f"{name}.csv", CSV_DIR)]
    keys = [d[KEYS[name]] for d in docs]
    unique = len(set(keys)) == len(keys)
    return FakeRepo([{**d, "_id": k if unique else f"{k}|{i}"} for i, (d, k) in enumerate(zip(docs, keys))])


class FakeDecisionRepo:
    def __init__(self):
        self.entries = []

    def add(self, entry):
        self.entries.append(dict(entry))
        return entry

    def get(self, decision_id):
        return next((e for e in self.entries if e["decision_id"] == decision_id), None)

    def for_items(self, item_type, ids):
        return sorted([e for e in self.entries if e["item_type"] == item_type and e["item_id"] in ids],
                      key=lambda e: e["created_at"])

    def since(self, created_at):
        return sorted([e for e in self.entries if e["created_at"] >= created_at], key=lambda e: e["created_at"],
                      reverse=True)


def decisions():
    from app.core.config import Settings
    from app.services.decision_service import DecisionService
    return DecisionService(FakeDecisionRepo(), Settings())


def real_stack():
    from app.core.config import Settings
    from app.services.comparison_service import ComparisonService
    from app.services.cost_service import CostService
    from app.services.operator_action_service import OperatorActionService
    from app.services.our_invoice_service import OurInvoiceService
    from app.services.scorecard_service import ScorecardService
    from app.services.suggestion_service import SuggestionService

    s = Settings()
    repos = {n: load(n) for n in ("devices", "weighbridge_tickets", "quality_assessments", "contracts", "contract_versions",
                                  "price_index_monthly", "material_classes", "collection_events", "invoices",
                                  "invoice_lines", "customers", "sites", "operators")}
    ours = OurInvoiceService(repos["devices"], repos["weighbridge_tickets"], repos["quality_assessments"], repos["contracts"],
                             repos["contract_versions"], repos["price_index_monthly"], repos["material_classes"], s)
    comparison = ComparisonService(repos["collection_events"], repos["invoices"], repos["invoice_lines"], decisions(), ours, s,
                                   repos["customers"], repos["sites"], repos["operators"])
    costs = CostService(comparison, repos["devices"], repos["sites"], s, load("telemetry_daily_summary"))
    actions = OperatorActionService(comparison, repos["contracts"], repos["contract_versions"], repos["devices"],
                                    repos["sites"], repos["material_classes"], repos["operators"],
                                    repos["weighbridge_tickets"], s)
    scorecard = ScorecardService(comparison, actions, SuggestionService(s), repos["collection_events"],
                                 repos["weighbridge_tickets"], repos["devices"], repos["sites"], repos["contracts"],
                                 repos["operators"], comparison.decisions, s)
    return comparison, costs, actions, scorecard
