from collections import defaultdict

from app.services.our_invoice_service import local_service_date


class MatchingService:
    def __init__(self, tz: str):
        self.tz = tz

    def match(self, invoices: list[dict], lines: list[dict], pickups: list[dict]) -> dict:
        contract_of = {i["invoice_id"]: i["contract_id"] for i in invoices}
        days = {p["collection_id"]: local_service_date(p, self.tz) for p in pickups}
        by_ref = {p["operator_job_ref"]: p for p in pickups if p.get("operator_job_ref")}
        by_day = defaultdict(list)
        for p in pickups:
            by_day[(p["contract_id"], days[p["collection_id"]])].append(p["collection_id"])

        result, by_pickup, seen, pending, monthly = {}, defaultdict(list), set(), [], []
        for ln in lines:
            if ln["line_type"] == "RENTAL":
                monthly.append(ln)
                continue
            contract = contract_of.get(ln["invoice_id"])
            p = by_ref.get(ln.get("operator_job_ref"))
            if p and p["contract_id"] == contract:
                self._attach(ln, p["collection_id"], "job_ref", result, by_pickup, seen)
            else:
                pending.append((ln, contract))
        for ln, contract in pending:
            cands = [pid for pid in by_day.get((contract, ln.get("service_date")), [])
                     if (pid, ln["line_type"]) not in seen]
            if cands:
                self._attach(ln, cands[0], "contract_date_type", result, by_pickup, seen)
            else:
                result[ln["invoice_line_id"]] = {"pickup_id": None, "status": "NO_LIFT", "match_by": None}
        return {"lines": result, "by_pickup": dict(by_pickup), "monthly": monthly, "days": days}

    @staticmethod
    def _attach(ln, pid, how, result, by_pickup, seen):
        key = (pid, ln["line_type"])
        status = "DUPLICATE" if key in seen and how == "job_ref" else "MATCHED"
        seen.add(key)
        result[ln["invoice_line_id"]] = {"pickup_id": pid, "status": status, "match_by": how}
        by_pickup[pid].append(dict(ln, match_status=status, match_by=how))
