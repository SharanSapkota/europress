from dataclasses import dataclass


@dataclass(frozen=True)
class Scope:
    customer_id: str
    site_id: str | None = None


class Scoped:
    def __init__(self, repo, field: str, allowed: set):
        self.repo = repo
        self.field = field
        self.allowed = allowed

    def _ok(self, doc) -> bool:
        return isinstance(doc, dict) and doc.get(self.field) in self.allowed

    def _filter(self, out):
        if isinstance(out, list):
            return [d for d in out if not isinstance(d, dict) or self._ok(d)]
        if isinstance(out, dict) and self.field in out:
            return out if self._ok(out) else None
        return out

    def periods(self) -> list[str]:
        return sorted({d["billing_period"] for d in self.repo.all() if self._ok(d) and d.get("billing_period")})

    def add(self, entry: dict) -> dict:
        if entry.get(self.field) not in self.allowed:
            raise PermissionError("Entry outside the customer scope")
        return self.repo.add(entry)

    def __getattr__(self, attr):
        value = getattr(self.repo, attr)
        if not callable(value):
            return value

        def call(*args, **kwargs):
            return self._filter(value(*args, **kwargs))
        return call


def scope_repos(base: dict, scope: Scope | None) -> dict:
    if scope is None:
        return dict(base, customer_sites=base["sites"])
    cid, sid = scope.customer_id, scope.site_id

    def mine(doc: dict) -> bool:
        return doc.get("customer_id") == cid and (not sid or doc.get("site_id") == sid)

    sites = {s["site_id"] for s in base["sites"].all() if mine(s)}
    devices = {d["device_id"] for d in base["devices"].all() if mine(d)}
    contracts = [c for c in base["contracts"].all() if mine(c)]
    contract_ids = {c["contract_id"] for c in contracts}
    pickups = [p for p in base["pickups"].all() if mine(p)]
    pickup_ids = {p["collection_id"] for p in pickups}
    job_refs = {p["operator_job_ref"] for p in pickups if p.get("operator_job_ref")}
    invoices = {i["invoice_id"] for i in base["invoices"].all()
                if i.get("customer_id") == cid and i.get("contract_id") in contract_ids}
    tickets = {t["ticket_id"] for t in base["tickets"].all() if t.get("operator_job_ref") in job_refs}
    operators = {c["operator_id"] for c in contracts} | {p["operator_id"] for p in pickups if p.get("operator_id")}
    out = dict(base, customer_sites=Scoped(base["sites"], "customer_id", {cid}))
    rules = {
        "devices": ("device_id", devices), "sites": ("site_id", sites), "contracts": ("contract_id", contract_ids),
        "pickups": ("collection_id", pickup_ids), "invoices": ("invoice_id", invoices),
        "lines": ("invoice_id", invoices), "versions": ("contract_id", contract_ids),
        "tickets": ("operator_job_ref", job_refs), "quality": ("ticket_id", tickets),
        "daily": ("device_id", devices), "telemetry": ("device_id", devices), "work_orders": ("device_id", devices),
        "calendar": ("site_id", sites), "operators": ("operator_id", operators), "customers": ("customer_id", {cid}),
        "decisions": ("customer_id", {cid}),
    }
    for name, (field, allowed) in rules.items():
        if name in base:
            out[name] = Scoped(base[name], field, allowed)
    return out
