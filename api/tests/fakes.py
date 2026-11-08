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


DEFAULT_PARAMS = {"pricing": {"price_per_device_month_eur": [29, 49, 79]},
                  "costs": {"onboarding_per_device_eur": 150, "operating_cost_per_device_month_eur": 9},
                  "adoption": {"adoption_share_of_eligible_pct": [20, 40]},
                  "equipment": {"lease_per_m3_month_eur": 15}}


def base_repos():
    names = {"devices": "devices", "sites": "sites", "contracts": "contracts", "pickups": "collection_events",
             "invoices": "invoices", "lines": "invoice_lines", "versions": "contract_versions",
             "tickets": "weighbridge_tickets", "quality": "quality_assessments", "daily": "telemetry_daily_summary",
             "work_orders": "maintenance_work_orders", "calendar": "site_calendar", "operators": "operators",
             "customers": "customers", "price_index": "price_index_monthly", "materials": "material_classes",
             "grade_rules": "quality_grade_rules"}
    base = {k: load(v) for k, v in names.items()}
    base.update(decisions=FakeDecisionRepo())
    return base


def services(customer_id=None, site_id=None, params=None, peers=True):
    from app.core.config import Settings
    from app.repositories.scope import Scope, scope_repos
    from app.services.registry import Services

    scope = Scope(customer_id, site_id) if customer_id else None
    return Services(scope_repos(base_repos(), scope), Settings(), DEFAULT_PARAMS if params is None else params,
                    customer_id, site_id, peers=peers and scope is None)


def real_stack():
    svc = services()
    return svc.comparison, svc.costs, svc.actions, svc.scorecard


def feature_stack(params=None):
    svc = services(params=params)
    return {"data": svc.data, "pickups": svc.pickups, "site_checks": svc.site_checks, "fleet": svc.fleet,
            "value": svc.value, "decisions": svc.decisions, "services": svc}
