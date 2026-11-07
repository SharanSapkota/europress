from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from pymongo.database import Database

EUR_FIELDS = {"amount_eur": "amount_cents", "unit_price_eur": "unit_price_cents", "total_eur": "total_cents"}


def _date_text(key: str, value: datetime) -> str:
    if key.endswith("_at"):
        ms = f".{value.microsecond // 1000:03d}" if value.microsecond else ""
        return value.strftime("%Y-%m-%dT%H:%M:%S") + ms + "Z"
    return value.strftime("%Y-%m" if key.endswith("month") else "%Y-%m-%d")


def to_domain(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    out = {k: _date_text(k, v) if isinstance(v, datetime) else v for k, v in doc.items()}
    for eur, cents in EUR_FIELDS.items():
        if out.get(eur) is not None:
            out[cents] = int((Decimal(str(out[eur])) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return out


class _Repo:
    name = ""
    key = "_id"

    def __init__(self, db: Database):
        self.col = db[self.name]

    def _find(self, query: dict, sort: list | None = None) -> list[dict]:
        cursor = self.col.find(query)
        return [to_domain(d) for d in (cursor.sort(sort) if sort else cursor)]

    def _one(self, query: dict) -> dict | None:
        return to_domain(self.col.find_one(query))

    def get(self, _id: str) -> dict | None:
        return self._one({self.key: _id})

    def all(self) -> list[dict]:
        return self._find({}, [(self.key, 1)])


class _CachedRepo(_Repo):
    def __init__(self, db: Database):
        super().__init__(db)
        self._docs: list[dict] | None = None

    def _all(self) -> list[dict]:
        if self._docs is None:
            self._docs = [to_domain(d) for d in self.col.find()]
        return self._docs

    def _find(self, query: dict, sort: list | None = None) -> list[dict]:
        docs = [d for d in self._all() if all(d.get(k) == v for k, v in query.items())]
        for field, direction in reversed(sort or []):
            docs.sort(key=lambda d: (d.get(field) is None, d.get(field)), reverse=direction < 0)
        return docs

    def _one(self, query: dict) -> dict | None:
        return next(iter(self._find(query)), None)


class DeviceRepository(_CachedRepo):
    name = "devices"
    key = "device_id"


class PickupRepository(_Repo):
    name = "collection_events"
    key = "collection_id"


class TicketRepository(_CachedRepo):
    name = "weighbridge_tickets"
    key = "ticket_id"

    def by_job_ref(self, ref: str) -> dict | None:
        return self._one({"operator_job_ref": ref})


class QualityRepository(_CachedRepo):
    name = "quality_assessments"
    key = "quality_assessment_id"

    def by_ticket(self, ticket_id: str) -> dict | None:
        return self._one({"ticket_id": ticket_id})


class ContractRepository(_CachedRepo):
    name = "contracts"
    key = "contract_id"


class ContractVersionRepository(_CachedRepo):
    name = "contract_versions"
    key = "contract_version_id"

    def for_contract(self, contract_id: str) -> list[dict]:
        return self._find({"contract_id": contract_id}, [("version_no", 1)])


class PriceIndexRepository(_CachedRepo):
    name = "price_index_monthly"
    key = "index_id"

    def price(self, index_id: str, month: str) -> dict | None:
        return self._one({"index_id": index_id, "month": month})


class MaterialRepository(_CachedRepo):
    name = "material_classes"
    key = "material_stream"


class OperatorInvoiceRepository(_Repo):
    name = "invoices"
    key = "invoice_id"

    def by_period(self, period: str) -> list[dict]:
        return self._find({"billing_period": period})

    def periods(self) -> list[str]:
        return sorted(self.col.distinct("billing_period"))


class OperatorInvoiceLineRepository(_Repo):
    name = "invoice_lines"
    key = "invoice_line_id"

    def by_invoices(self, invoice_ids: list[str]) -> list[dict]:
        return self._find({"invoice_id": {"$in": invoice_ids}}, [("invoice_id", 1), ("line_no", 1)])


class TelemetryRepository(_Repo):
    name = "telemetry_hourly"
    key = "message_id"

    def readings(self, device_id: str, start: str | None = None, end: str | None = None) -> list[dict]:
        query: dict = {"device_id": device_id}
        span = {op: datetime.fromisoformat(v.replace("Z", "+00:00")) for op, v in (("$gte", start), ("$lt", end)) if v}
        if span:
            query["measured_at"] = span
        seen, out = set(), []
        for d in self._find(query, [("measured_at", 1), ("ingest_seq", 1)]):
            if d["message_id"] not in seen:
                seen.add(d["message_id"])
                out.append(d)
        return out


class CustomerRepository(_CachedRepo):
    name = "customers"
    key = "customer_id"


class SiteRepository(_CachedRepo):
    name = "sites"
    key = "site_id"


class OperatorRepository(_CachedRepo):
    name = "operators"
    key = "operator_id"


class TelemetryDailyRepository(_Repo):
    name = "telemetry_daily_summary"
    key = "device_id"

    def for_devices(self, device_ids: list[str], start_month: str, end_month: str) -> list[dict]:
        start = datetime.strptime(start_month, "%Y-%m").replace(tzinfo=timezone.utc)
        last = datetime.strptime(end_month, "%Y-%m")
        end = datetime(last.year + last.month // 12, last.month % 12 + 1, 1, tzinfo=timezone.utc)
        return self._find({"device_id": {"$in": device_ids}, "date": {"$gte": start, "$lt": end}})


class DecisionRepository(_Repo):
    name = "decisions"
    key = "decision_id"

    def add(self, entry: dict) -> dict:
        self.col.insert_one(dict(entry))
        return entry

    def for_items(self, item_type: str, item_ids: list[str]) -> list[dict]:
        return self._find({"item_type": item_type, "item_id": {"$in": item_ids}}, [("created_at", 1)])

    def since(self, created_at: str) -> list[dict]:
        return self._find({"created_at": {"$gte": created_at}}, [("created_at", -1)])
