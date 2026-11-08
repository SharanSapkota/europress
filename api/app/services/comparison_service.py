import re
from datetime import date

from app.core.config import Settings
from app.services.explain import listing, why
from app.services.matching_service import MatchingService
from app.services.our_invoice_service import OurInvoiceService, invoice_tonnage, local_service_date
from app.services.pricing import LIFT_STATUSES, MASS_LINES

STATUS_ORDER = ("CHECK", "NO_DATA", "EXPLAINED", "MATCH", "DISPUTED")
WEIGHT_FAMILIES = ("WEIGHT_DISCREPANCY", "WEIGHT_UNVERIFIED", "WEIGHT_BASIS_MISMATCH", "GRADE_NOT_SHARED")
DECISIONS = {"question": "dispute_sent"}
CAUSE = {"WEIGHT_DISCREPANCY": "measurement", "WEIGHT_UNVERIFIED": "data", "GRADE_NOT_SHARED": "data"}
CAUSE_TEXT = {"invoice": "Billed lift compared with your contract", "measurement": "Device or weighbridge measurement",
              "data": "Missing data", "normal": "Normal operation"}


SHORT = {
    "DUPLICATE_LINE": "{} billed twice", "UNMATCHED_LINE": "{} with no matching pickup",
    "WRONG_SURCHARGE": "{} differs from your contract", "OUTDATED_TARIFF": "{} at an old rate",
    "MISSING_LINE": "{} not billed", "UNINVOICED_COLLECTION": "Pickup not on the invoice",
    "RATE_DIFFERENCE": "{} rate differs from your contract", "AMOUNT_DIFFERENCE": "{} amount differs",
    "UNEXPECTED_LINE": "{} not in your contract", "WEIGHT_DISCREPANCY": "Scale weight differs from the device",
    "WEIGHT_UNVERIFIED": "Billed weight not confirmed by a scale ticket", "GRADE_NOT_SHARED": "Quality grade not shared",
}


def short_reason(item: dict | None) -> str | None:
    if not item:
        return None
    if item["family"] == "WEIGHT_BASIS_MISMATCH":
        return f"Billed weight {'above' if item['euros_at_stake_cents'] > 0 else 'below'} scale ticket"
    return SHORT.get(item["family"], "{} differs").format(label(item.get("line_type") or "") or "Charge")


def cause_of(item: dict | None, status: str) -> str | None:
    if status == "MATCH":
        return None
    if status == "NO_DATA" and (not item or item["status"] != "NO_DATA"):
        return "data"
    if not item:
        return None
    if item["status"] == "EXPLAINED":
        return "normal"
    return CAUSE.get(item["family"], "invoice")
SURCHARGES = ("FUEL_SURCHARGE", "REMOTE_SURCHARGE", "EMERGENCY_SURCHARGE", "SIDE_WASTE_FEE")
GRADE_LINES = ("CONTAMINATION_PENALTY", "REJECTION_REPROCESSING", "PROCESSING", "MATERIAL_CREDIT", "MIN_CHARGE_TOPUP")
LABELS = {
    "LIFT_FEE": "Lift fee", "TRANSPORT": "Transport", "REMOTE_SURCHARGE": "Remote surcharge",
    "FUEL_SURCHARGE": "Fuel surcharge", "HAUL_PER_TONNE": "Haul per tonne", "PROCESSING": "Processing",
    "REJECTION_REPROCESSING": "Reprocessing", "MIN_CHARGE_TOPUP": "Minimum charge top-up",
    "MATERIAL_CREDIT": "Material credit", "CONTAMINATION_PENALTY": "Contamination fee",
    "SIDE_WASTE_FEE": "Side waste fee", "EMERGENCY_SURCHARGE": "Emergency surcharge",
    "CANCELLATION_FEE": "Cancellation fee", "WASTED_TRIP_FEE": "Wasted trip fee", "RENTAL": "Rental",
}
WEIGHT_SOURCE = {"ticket": "Weighbridge ticket {}", "invoice": "Invoice item {}", "device": "Device {} estimate"}


def label(line_type: str) -> str:
    return LABELS.get(line_type, line_type.replace("_", " ").capitalize())


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "June", "July", "Aug", "Sept", "Oct", "Nov", "Dec")
WEIGHT_NOTE = {"ticket": "scale ticket", "device": "device estimate", "invoice": "billed quantity"}


def tonnes(kg: int | float) -> str:
    return f"{round(kg / 1000, 2):g}".replace(".", ",") + " t"


def short_day(iso: str | None) -> str:
    if not iso:
        return "–"
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month - 1]}"


def version_no(vid: str | None) -> str | None:
    m = re.search(r"-V(\d+)$", vid or "")
    return m.group(1) if m else None


def lifts(n: int, tail: str) -> str:
    return f"{n} {'lift' if n == 1 else 'lifts'}{tail}"


def material_text(m: str | None) -> str:
    return (m or "waste").replace("_", " ")


def dispute_message(invoice: str | None, opening: str, check: str, diff_cents: int) -> str:
    where = f"On invoice {invoice}, " if invoice else "On your invoice, "
    return (f"Hello,\n\n{where}{opening}{(' ' + check) if check else ''}\n\n"
            f"Could you please check this lift and correct it if needed? The difference is {eur(diff_cents)}.\n\n"
            f"Thank you,")


def view_of(row: dict) -> str:
    if row["status"] == "DISPUTED":
        return "disputed"
    if row["status"] == "EXPLAINED":
        return "explained"
    return "check" if row["status"] != "MATCH" and row["needs_attention"] else "match"


STORED_TARE_REASON = ("The operator used a stored truck weight. That can explain the gap, "
                      "or the stored weight may be out of date.")


def eur(cents: int) -> str:
    return f"{abs(cents) / 100:,.2f}".replace(",", " ").replace(".", ",") + " €"


def how_sure(confidence: str, weight: dict | None = None) -> str:
    src = (weight or {}).get("source")
    if confidence == "Not enough data" or (weight is not None and src is None):
        return "Not enough data: there is no scale ticket and no device weight for this pickup."
    if src == "device":
        return f"Not sure: our weight is the device estimate (± {weight['range_kg']} kg), no scale ticket was shared."
    if src == "invoice":
        return "Not sure: our weight is the operator's own invoice quantity, no scale ticket was shared."
    if confidence == "high":
        return "Sure: the numbers come from the invoice, the scale ticket and your contract."
    return "Fairly sure: the numbers come from your contract and the operator's records, but one input is uncertain."


def draft(action: str, what: str, ref: str, invoice: str, detail: str) -> str:
    if action in ("REQUEST_TICKET", "REQUEST_WEIGHBRIDGE_DATA"):
        ask = ("Could you please share the weighbridge ticket for this pickup (gross, tare and net weight)? "
               "It would help us confirm the billed weight.")
    else:
        ask = "Could you please check this lift and let us know? We may have missed something on our side."
    return (f"Hello,\n\nWe are going through invoice {invoice} and have a question about {what} "
            f"(job reference {ref}).\n\n{detail}\n\n{ask}\n\nThank you for your help.\n\nBest regards,")


def part(ln: dict) -> dict:
    return {"quantity": ln.get("quantity"), "unit": ln.get("unit"), "rate_cents": ln.get("unit_price_cents"),
            "amount_cents": ln.get("amount_cents") or 0}


class ComparisonService:
    def __init__(self, pickups, invoices, lines, decisions, our_invoices: OurInvoiceService, settings: Settings,
                 customers=None, sites=None, operators=None):
        self.customers = customers
        self.sites = sites
        self.operators = operators
        self.pickups = pickups
        self.invoices = invoices
        self.lines = lines
        self.decisions = decisions
        self.ours = our_invoices
        self.s = settings
        self.matcher = MatchingService(settings.local_tz)

    def customer_id(self, customer_id: str | None = None) -> str | None:
        if customer_id or self.s.customer_id:
            return customer_id or self.s.customer_id
        first = self.customers.all() if self.customers else []
        return first[0]["customer_id"] if first else None

    def names(self, site_ids: list[str], operator_ids: list[str], customer_id: str | None) -> dict:
        def name(repo, _id, field):
            return ((repo.get(_id) if repo else None) or {}).get(field) or _id
        return {"customer_name": name(self.customers, customer_id, "customer_name") if customer_id else None,
                "site_names": [name(self.sites, i, "site_name") for i in site_ids],
                "operator_names": [name(self.operators, i, "operator_name") for i in operator_ids]}

    def compare(self, period: str, customer_id: str | None = None, everyone: bool = False) -> dict:
        cid = None if everyone else self.customer_id(customer_id)
        invoices = [i for i in self.invoices.by_period(period) if not cid or i.get("customer_id") == cid]
        op_lines = self.lines.by_invoices([i["invoice_id"] for i in invoices])
        pickups = {p["collection_id"]: p for p in self.pickups.all() if not cid or p.get("customer_id") == cid}
        m = self.matcher.match(invoices, op_lines, list(pickups.values()))
        ids = set(m["by_pickup"]) | {pid for pid, d in m["days"].items() if d and d[:7] == period}
        rows = [self._row(pickups[pid], m["by_pickup"].get(pid, []), period) for pid in ids]
        rows = [r for r in rows if r["lines"]]
        decided = self.decisions.current("invoice_item", [r["pickup_id"] for r in rows])
        for r in rows:
            self._apply_decision(r, decided.get(r["pickup_id"]))
            if r["difference_cents"] == 0 and r["status"] != "DISPUTED":
                r["status"], r["needs_attention"] = "MATCH", False
            r["view"] = view_of(r)
        rows.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), r["date"] or "", r["pickup_id"]))

        by_id = {ln["invoice_line_id"]: ln for ln in op_lines}
        inv_op = {i["invoice_id"]: i.get("operator_id") for i in invoices}
        no_lift = [by_id[lid] for lid, res in m["lines"].items() if res["status"] == "NO_LIFT"]
        unmatched = [{
            "family": "UNMATCHED_LINE", "entity_type": "invoice_line", "entity_id": ln["invoice_line_id"],
            "status": "CHECK", "line_type": ln["line_type"], "label": label(ln["line_type"]),
            "service_date": ln.get("service_date"), "operator_job_ref": ln.get("operator_job_ref"),
            "euros_at_stake_cents": ln.get("amount_cents") or 0, "confidence": "high",
            "reason": f"{label(ln['line_type'])} on {ln.get('service_date')} (job {ln.get('operator_job_ref')}) "
                      f"has no matching pickup by job reference or by contract, date and charge type.",
            "sources": {"operator_amount": f"Invoice item {ln['invoice_line_id']}"},
            "invoice_id": ln["invoice_id"], "operator_id": inv_op.get(ln["invoice_id"]),
            "suggested_action": "CORRECT_LINE",
            "explain": {"what": f"The invoice has a {label(ln['line_type']).lower()} of {eur(ln.get('amount_cents') or 0)} "
                                f"on {ln.get('service_date')} that we cannot link to a pickup.",
                        "why": "The job reference and the contract, date and charge type do not match any pickup we have.",
                        "how_sure": how_sure("high")},
            "why": {"amount": why(f"{label(ln['line_type'])} of {eur(ln.get('amount_cents') or 0)} on the invoice",
                                  f"Invoice item {ln['invoice_line_id']}", "high",
                                  "No pickup matches its job reference, or its contract, date and charge type.",
                                  "observed")},
            "cause": "invoice", "cause_text": CAUSE_TEXT["invoice"],
            "trail": {"invoice_line_ids": [ln["invoice_line_id"]], "operator_job_ref": ln.get("operator_job_ref"),
                      "invoice_ids": [ln["invoice_id"]]},
            "needs_attention": True, "short_reason": f"{label(ln['line_type'])} with no matching pickup",
            "ours_note": "No pickup found", "billed_note": f"{label(ln['line_type'])} billed",
            "dispute_message": dispute_message(
                ln["invoice_id"], f"there is a {label(ln['line_type']).lower()} of {eur(ln.get('amount_cents') or 0)} "
                f"on {short_day(ln.get('service_date'))} that we cannot link to a pickup.", "",
                ln.get("amount_cents") or 0),
            "dispute": {"invoice_id": ln["invoice_id"], "line_no": ln.get("line_no"),
                        "invoice_line_id": ln["invoice_line_id"], "operator_email": None},
            "draft_question": draft(
                "CHECK_LINE", f"the {label(ln['line_type']).lower()} on {ln.get('service_date')}",
                ln.get("operator_job_ref") or "not given", ln["invoice_id"],
                f"Invoice item {ln['invoice_line_id']} ({eur(ln.get('amount_cents') or 0)}) does not seem to belong "
                f"to any pickup we have on record."),
        } for ln in no_lift]
        line_decisions = self.decisions.current("invoice_item", [u["entity_id"] for u in unmatched])
        for u in unmatched:
            self._apply_decision(u, line_decisions.get(u["entity_id"]))
            u["view"] = "disputed" if u["status"] == "DISPUTED" else "check"
        unmatched_cents = sum(u["euros_at_stake_cents"] for u in unmatched)
        ours = sum(r["ours"]["amount_cents"] for r in rows)
        operator = sum(r["operator"]["amount_cents"] for r in rows) + unmatched_cents
        site_ids = sorted({r["site_id"] for r in rows if r["site_id"]})
        operator_ids = sorted({r["operator_id"] for r in rows if r["operator_id"]} | {i["operator_id"] for i in invoices if i.get("operator_id")})
        return {
            "period": period, "tolerance_pct": self.s.tolerance_pct, "customer_id": cid,
            "site_ids": site_ids, "operator_ids": operator_ids, **self.names(site_ids, operator_ids, cid),
            "invoices": [{"invoice_id": i["invoice_id"], "contract_id": i.get("contract_id"),
                          "operator_id": i.get("operator_id"), "issued_at": i.get("issued_at"),
                          "dispute_status": i.get("dispute_status"), "total_cents": i.get("total_cents")} for i in invoices],
            "totals": {"ours_cents": ours, "operator_cents": operator, "difference_cents": operator - ours,
                       "unmatched_cents": unmatched_cents,
                       "monthly_fixed_cents": sum(ln.get("amount_cents") or 0 for ln in m["monthly"])},
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER},
            "line_total": len([ln for ln in op_lines if ln["line_type"] != "RENTAL"]),
            "attention_count": sum(1 for r in rows if r["needs_attention"]) + len(unmatched),
            "match_count": sum(1 for r in rows if not r["needs_attention"]),
            "line_counts": {s: sum(1 for res in m["lines"].values() if res["status"] == s)
                            for s in ("MATCHED", "DUPLICATE", "NO_LIFT")},
            "view_counts": {v: sum(1 for x in rows + unmatched if x["view"] == v)
                            for v in ("check", "disputed", "explained", "match")},
            "unmatched_lines": unmatched,
            "rows": rows,
            "why": self._totals_why(rows, invoices, unmatched),
        }

    @staticmethod
    def _totals_why(rows: list[dict], invoices: list[dict], unmatched: list[dict]) -> dict:
        weak = [r for r in rows if r["ours"]["weight_source"] != "ticket"]
        conf = "high" if not weak else "low"
        versions = listing([r["contract_version_id"] for r in rows], "Contract versions")
        sure = (f"{len(weak)} of {len(rows)} pickups have no scale ticket, so their weight is an estimate."
                if weak else "Every weight comes from a scale ticket.")
        return {
            "ours": why(f"Sum of our estimates for {len(rows)} pickups.", versions, conf, sure),
            "operator": why(f"Sum of {len(invoices)} operator invoices, including {len(unmatched)} charges without a pickup.",
                            listing([i["invoice_id"] for i in invoices], "Invoices"), "high", None, "observed"),
            "difference": why("Operator invoice minus our estimate.", f"{versions}; "
                              f"{listing([i['invoice_id'] for i in invoices], 'invoices')}", conf, sure),
        }

    def detail(self, pickup_id: str) -> dict | None:
        p = self.pickups.get(pickup_id)
        if not p:
            return None
        day = local_service_date(p, self.s.local_tz)
        return next((r for r in self.compare(day[:7])["rows"] if r["pickup_id"] == pickup_id), None) if day else None

    def periods(self) -> list[str]:
        return self.invoices.periods()

    def data_months(self) -> list[str]:
        days = {local_service_date(p, self.s.local_tz) for p in self.pickups.all()}
        return sorted({d[:7] for d in days if d} | set(self.periods()))

    def find_item(self, item_id: str) -> dict | None:
        for period in reversed(self.periods()):
            res = self.compare(period)
            for r in res["rows"]:
                if r["pickup_id"] == item_id:
                    mat = material_text(r["material"]).capitalize()
                    vno = version_no(r["contract_version_id"])
                    dev = r["device_kg"]
                    evidence = {"pickup_id": r["pickup_id"], "date": r["date"], "material": r["material"],
                                "invoice_id": (r["invoice_ids"] or [None])[0], "operator_job_ref": r["operator_job_ref"],
                                "our_scale_kg": dev, "our_scale_range_kg": r["ours"]["range_kg"],
                                "ticket_id": r["ticket_id"], "ticket_kg": r["ticket_kg"],
                                "billed_kg": r["operator"]["billed_kg"], "weight_source": r["ours"]["weight_source"],
                                "contract_version_id": r["contract_version_id"],
                                "should_cost_cents": r["ours"]["amount_cents"], "billed_cents": r["operator"]["amount_cents"],
                                "difference_cents": r["difference_cents"]}
                    billed = r["operator"]["billed_kg"]
                    view = {"title": f"Lift, {short_day(r['date'])}",
                            "detail": f"{mat} · {(r['short_reason'] or 'matches your contract').lower()}",
                            "trail": [{"label": "Pickup", "value": f"{short_day(r['date'])} · {mat}"},
                                      {"label": "Our scale", "value": f"{tonnes(dev)}" + (
                                          f" ± {tonnes(r['ours']['range_kg'])}" if r["ours"]["range_kg"] else "")
                                       if dev is not None else "No reading"},
                                      {"label": "Scale ticket",
                                       "value": tonnes(r["ticket_kg"]) if r["ticket_kg"] is not None else "Not shared"},
                                      {"label": "Contract", "value": f"Version {vno}" if vno else "Not found"},
                                      {"label": "Billed", "value": (f"{tonnes(billed)} · " if billed is not None else "")
                                       + eur(r["operator"]["amount_cents"])}]}
                    return {"label": f"{mat} pickup on {r['date']}", "evidence": evidence, "view": view,
                            "action": r["suggested_action"], "text": r["reason"],
                            "numbers": {"ours_cents": r["ours"]["amount_cents"],
                                        "operator_cents": r["operator"]["amount_cents"],
                                        "difference_cents": r["difference_cents"], "weight_kg": r["ours"]["weight_kg"],
                                        "billed_kg": r["operator"]["billed_kg"], "status": r["found_status"],
                                        "operator_job_ref": r["trail"]["operator_job_ref"],
                                        "ticket_id": r["trail"]["ticket_id"],
                                        "contract_version_id": r["trail"]["contract_version_id"],
                                        "invoice_line_ids": ", ".join(r["trail"]["invoice_line_ids"])}}
            for u in res["unmatched_lines"]:
                if u["entity_id"] == item_id:
                    view = {"title": f"{u['label']}, {short_day(u['service_date'])}", "detail": "No matching pickup",
                            "trail": [{"label": "Invoice", "value": u["invoice_id"]},
                                      {"label": "Billed", "value": eur(u["euros_at_stake_cents"])}]}
                    evidence = {"invoice_id": u["invoice_id"], "invoice_line_id": u["entity_id"], "date": u["service_date"],
                                "operator_job_ref": u["operator_job_ref"], "billed_cents": u["euros_at_stake_cents"],
                                "difference_cents": u["euros_at_stake_cents"]}
                    return {"label": f"{u['label']} on {u['service_date']} without a pickup", "evidence": evidence,
                            "view": view, "action": u["suggested_action"], "text": u["reason"],
                            "numbers": {"operator_cents": u["euros_at_stake_cents"], "status": u["found_status"],
                                        "operator_job_ref": u["operator_job_ref"], "invoice_line_ids": u["entity_id"]}}
        return None

    def decide(self, item_id: str, decision: str, message: str | None = None) -> dict | None:
        item = self.find_item(item_id)
        if not item:
            return None
        view = dict(item["view"], suggestion="Submit a dispute" if decision != "ok" else "No action")
        return self.decisions.record("invoice_item", item_id, decision, item["label"],
                                     {"action": item["action"], "text": item["text"]}, item["numbers"],
                                     evidence=item["evidence"], message=message, view=view)

    @staticmethod
    def _apply_decision(item: dict, d: dict | None) -> None:
        d = d or {}
        decision = DECISIONS.get(d.get("decision"), d.get("decision"))
        item["found_status"] = item["status"]
        item["decision"], item["decided_at"] = decision, d.get("created_at")
        item["decision_id"] = d.get("decision_id")
        item["disputed_at"] = d.get("created_at") if decision == "dispute_sent" else None
        if decision == "dispute_sent":
            item["status"] = "DISPUTED"

    @staticmethod
    def _row_why(ours, w, theirs, inv_ids, op_total, billed, reason, conf, period, lines, items) -> dict:
        vid = ours["contract_version_id"]
        weight_src = WEIGHT_SOURCE[w["source"]].format(w["source_id"]) if w["source"] else None
        ours_src = "; ".join(x for x in (f"Contract version {vid}" if vid else None, weight_src) if x) or None
        op_src = f"Invoice {', '.join(inv_ids)}" if inv_ids else f"Not on any operator invoice for {period}"
        reasons = {i["entity_id"]: i["reason"] for i in items if i["entity_type"] == "invoice_line"}
        by_type = {i["line_type"]: i["reason"] for i in items if i.get("line_type")}
        for lr in lines:
            mass = lr["line_type"] in MASS_LINES
            line_conf = "high" if not mass or w["source"] == "ticket" else w["confidence"]
            src = "; ".join(x for x in (lr["our_source"], lr["operator_source"]) if x) or None
            lr["why"] = why(f"{lr['label']}: our estimate and the invoice.", src, line_conf,
                            (reasons.get(lr["invoice_line_id"]) or by_type.get(lr["line_type"]))
                            if lr["status"] == "CHECK" else None)
        out = {
            "ours": why(f"Our estimate {eur(ours['total_cents'])} from your contract and our weight.", ours_src,
                        w["confidence"] if w["source"] or not ours["lines"] else "not enough data"),
            "operator": why(f"Operator invoice {eur(op_total)} for this pickup.", op_src, "high", None, "observed"),
            "difference": why("Operator invoice minus our estimate.", f"{ours_src or 'Your contract'}; {op_src}",
                              conf, reason),
        }
        if w["kg"] is not None or billed is not None:
            gap = None if billed is None or w["kg"] is None else f"The billed weight is {billed - w['kg']:+d} kg from our weight"
            spread = f"the device estimate is ± {w['range_kg']} kg" if w["source"] == "device" else None
            text = "; ".join(x for x in (gap, spread) if x)
            out["weight"] = why(f"Our weight {w['kg']} kg" + (f", billed {billed} kg." if billed is not None else "."),
                                weight_src, w["confidence"], f"{text[0].upper()}{text[1:]}." if text else None,
                                "estimated" if w["source"] == "device" else "observed")
        return out

    def _should_why(self, ours: dict, w: dict, has_mass: bool) -> dict:
        n = version_no(ours["contract_version_id"])
        contract = f"Your contract (version {n})" if n else "Your contract"
        what = f"Should cost {eur(ours['total_cents'])} (estimate)."
        if not has_mass:
            return {"what": what, "source": f"{contract}, fixed fees per lift.", "confidence": "high",
                    "reason": "Fixed fees from your contract. No weight is needed.", "evidence": "observed"}
        src, kg, dev = w["source"], w["kg"], ours["device_kg"]
        if src is None or kg is None:
            return {"what": what, "source": f"{contract}. No weight yet.", "confidence": "low",
                    "reason": "Not enough data: no scale ticket and no container scale weight.", "evidence": "estimated"}
        if src == "ticket":
            where = f"the operator's own scale ticket of {short_day(ours['service_date'])}: {tonnes(kg)}"
            if dev is None:
                conf, sure = "high", "The scale ticket is the official weight. There is no container scale reading."
            elif abs(dev - kg) * 100 <= self.s.weight_tolerance_pct * max(kg, 1):
                conf, sure = "high", f"Our container scale says {tonnes(dev)} too."
            else:
                conf, sure = "medium", f"Our container scale says {tonnes(dev)}. The scale ticket is used."
        elif src == "device":
            where = f"our container scale: {tonnes(kg)}" + (f" ± {tonnes(w['range_kg'])}" if w["range_kg"] else "")
            conf, sure = "medium", "No scale ticket yet. The container scale has a small margin."
        else:
            where = f"the operator's billed quantity: {tonnes(kg)}"
            conf, sure = "low", "Only the operator's own quantity. No scale ticket and no container scale weight."
        return {"what": what, "source": f"{contract} × {where}.", "confidence": conf, "reason": sure,
                "evidence": "observed" if src == "ticket" else "estimated"}

    def _action(self, status: str, items: list[dict], lines: list[dict], ours: dict) -> str:
        if status in ("MATCH", "EXPLAINED"):
            return "NONE"
        if status == "NO_DATA":
            return "REQUEST_TICKET"
        open_items = [i for i in items if i["status"] == "CHECK"]
        weight_related = any(i["family"] in WEIGHT_FAMILIES for i in open_items) or any(
            lr["status"] == "CHECK" and lr["line_type"] in MASS_LINES and not lr["duplicate"] for lr in lines)
        if not weight_related:
            return "CORRECT_LINE"
        ticket, dev = ours["ticket"], ours["device_kg"]
        if not ticket:
            return "REQUEST_TICKET"
        ref = max(0, int(ticket["allocated_net_kg"] or 0))
        agree = dev is None or abs(dev - ref) * 100 <= self.s.weight_tolerance_pct * max(ref, 1)
        return "CORRECT_LINE" if agree else "REQUEST_TICKET"

    def _tol(self, amount: int) -> float:
        return abs(amount) * self.s.tolerance_pct / 100

    def _lines(self, ours: dict, theirs: list[dict]) -> list[dict]:
        vid = ours["contract_version_id"]
        main = [ln for ln in theirs if ln["match_status"] == "MATCHED"]
        out = []
        for t in dict.fromkeys([ln["line_type"] for ln in ours["lines"]] + [ln["line_type"] for ln in main]):
            mine = next((ln for ln in ours["lines"] if ln["line_type"] == t), None)
            op = next((ln for ln in main if ln["line_type"] == t), None)
            ours_amt = mine["amount_cents"] if mine else 0
            op_amt = (op or {}).get("amount_cents") or 0
            diff = op_amt - ours_amt
            ok = mine is not None and op is not None and abs(diff) <= self._tol(ours_amt)
            out.append({
                "line_type": t, "label": label(t),
                "ours": {k: mine[k] for k in ("quantity", "unit", "rate_cents", "amount_cents")} if mine else None,
                "operator": part(op) if op else None, "difference_cents": diff, "duplicate": False,
                "status": "MATCH" if ok or (not mine and not op_amt) else "CHECK",
                "our_source": f"Contract version {vid}" if mine else None,
                "operator_source": f"Invoice item {op['invoice_line_id']}" if op else None,
                "invoice_line_id": op["invoice_line_id"] if op else None,
                "invoice_id": op["invoice_id"] if op else None,
            })
        for ln in theirs:
            if ln["match_status"] == "DUPLICATE":
                out.append({"line_type": ln["line_type"], "label": f"{label(ln['line_type'])} (again)", "ours": None,
                            "operator": part(ln), "difference_cents": ln.get("amount_cents") or 0, "duplicate": True,
                            "status": "CHECK", "our_source": None,
                            "operator_source": f"Invoice item {ln['invoice_line_id']}",
                            "invoice_line_id": ln["invoice_line_id"], "invoice_id": ln["invoice_id"]})
        return out

    def _older_rate(self, ours: dict, line_type: str, rate) -> str | None:
        field = {"LIFT_FEE": "lift_fee_cents", "TRANSPORT": "per_km_cents", "REMOTE_SURCHARGE": "remote_surcharge_cents",
                 "HAUL_PER_TONNE": "haul_fee_cents_per_t", "PROCESSING": "processing_fee_cents_per_t"}.get(line_type)
        if not field or rate is None:
            return None
        for v in self.ours.versions.for_contract(ours["contract_id"]):
            if v["contract_version_id"] != ours["contract_version_id"] and v["effective_from"] < (ours["service_date"] or "") \
                    and int(v[field]) == rate:
                return v["contract_version_id"]
        return None

    def _line_items(self, ours: dict, lines: list[dict], grade_unknown: bool) -> list[dict]:
        items, vid = [], ours["contract_version_id"]
        ticket = ours["ticket"]
        for lr in lines:
            if lr["status"] != "CHECK":
                continue
            lbl, diff = lr["label"], lr["difference_cents"]
            item = {"entity_type": "invoice_line", "entity_id": lr["invoice_line_id"], "status": "CHECK",
                    "euros_at_stake_cents": diff, "confidence": "high", "line_type": lr["line_type"],
                    "invoice_id": lr.get("invoice_id"),
                    "sources": {"our_amount": lr["our_source"], "operator_amount": lr["operator_source"]}}
            if lr["duplicate"]:
                item.update(family="DUPLICATE_LINE",
                            reason=f"{label(lr['line_type'])} for this pickup appears twice on the invoice.")
            elif grade_unknown and lr["line_type"] in GRADE_LINES:
                item.update(family="GRADE_NOT_SHARED", status="NO_DATA", confidence="Not enough data",
                            entity_type="collection", entity_id=ours["pickup_id"],
                            reason=f"{lbl} depends on the quality grade, which the operator has not shared.")
            elif lr["operator"] is None:
                item.update(family="MISSING_LINE", entity_type="collection", entity_id=ours["pickup_id"],
                            reason=f"{lbl} from contract version {vid} is not on the invoice for this pickup.")
            elif lr["ours"] is None:
                item.update(family="UNEXPECTED_LINE", confidence="medium",
                            reason=f"{lbl} is on the invoice but contract version {vid} does not give it for this pickup.")
            elif lr["line_type"] in MASS_LINES and ticket and lr["ours"]["quantity"] != lr["operator"]["quantity"]:
                item.update(family="WEIGHT_BASIS_MISMATCH",
                            reason=f"{lbl} is billed on {round(lr['operator']['quantity'] * 1000)} kg; weighbridge "
                                   f"ticket {ticket['ticket_id']} says {round(lr['ours']['quantity'] * 1000)} kg.")
            elif lr["ours"]["rate_cents"] != lr["operator"]["rate_cents"] or lr["ours"]["unit"] == "pct_of_base":
                old = self._older_rate(ours, lr["line_type"], lr["operator"]["rate_cents"])
                if old:
                    item.update(family="OUTDATED_TARIFF",
                                reason=f"{lbl} uses the rate of {old}; {vid} was valid on {ours['service_date']}.")
                elif lr["line_type"] in SURCHARGES:
                    item.update(family="WRONG_SURCHARGE",
                                reason=f"{lbl} on the invoice differs from contract version {vid}.")
                else:
                    item.update(family="RATE_DIFFERENCE",
                                reason=f"{lbl} rate differs from contract version {vid}.")
            else:
                item.update(family="AMOUNT_DIFFERENCE", confidence="medium",
                            reason=f"{lbl} amount differs from contract version {vid} by {eur(diff)}.")
            items.append(item)
        return items

    def _weight_item(self, ours: dict, billed: int | None) -> dict | None:
        ticket, dev, pid = ours["ticket"], ours["device_kg"], ours["pickup_id"]
        if dev is None:
            return None
        ref = max(0, int(ticket["allocated_net_kg"])) if ticket else billed
        if ref is None or abs(dev - ref) * 100 <= self.s.weight_tolerance_pct * max(ref, 1):
            return None
        stake = ours["total_cents"] - self.ours.reprice(ours, dev)
        pct = round((dev - ref) * 100 / max(ref, 1))
        base = {"entity_type": "collection", "entity_id": pid, "euros_at_stake_cents": stake,
                "sources": {"device_weight": f"Device {ours['device_id']} estimate",
                            "billed_weight": f"Weighbridge ticket {ticket['ticket_id']}" if ticket else
                            f"Invoice item {(ours['weight'] or {}).get('source_id')}"}}
        if not ticket:
            return dict(base, family="WEIGHT_UNVERIFIED", status="CHECK", confidence="low",
                        reason=f"Billed weight {ref} kg, device weight {dev} kg ({pct:+d}%); "
                               f"no weighbridge ticket was shared to confirm either.")
        why, ruled_out = [], []
        if (ticket.get("loads_on_vehicle") or 1) > 1:
            why.append(f"combined load ({ticket['loads_on_vehicle']} pickups on one truck, weight split equally)")
        else:
            ruled_out.append("not a combined load")
        if any(ln["line_type"] == "SIDE_WASTE_FEE" for ln in ours["lines"]):
            why.append("side waste loaded at the same pickup")
        else:
            ruled_out.append("no side waste reported")
        stored = ticket.get("tare_method") == "STORED"
        if stored and self.s.stored_tare_explains:
            why.append("stored truck tare used at the weighbridge")
        elif not stored:
            ruled_out.append("tare was weighed")
        head = f"Device weight {dev} kg, weighbridge ticket {ref} kg ({pct:+d}%)"
        if why:
            return dict(base, family="WEIGHT_DISCREPANCY", status="EXPLAINED", confidence="medium",
                        reason=f"{head}: likely {' and '.join(why)}.")
        if stored:
            return dict(base, family="WEIGHT_DISCREPANCY", status="CHECK", confidence="low", reason=STORED_TARE_REASON)
        return dict(base, family="WEIGHT_DISCREPANCY", status="CHECK", confidence="medium",
                    reason=f"{head}; {', '.join(ruled_out)}.")

    def _row(self, pickup: dict, theirs: list[dict], period: str) -> dict:
        ours = self.ours.for_pickup(pickup, theirs)
        lines = self._lines(ours, theirs)
        op_total = sum(ln.get("amount_cents") or 0 for ln in theirs)
        tonnage = invoice_tonnage(theirs)
        billed = round(tonnage["quantity"] * 1000) if tonnage else None
        w, vid = ours["weight"], ours["contract_version_id"]
        grade_unknown = bool(ours["price_args"]["credit_eligible"]) and not ours["grade_source"]
        has_mass = any(lr["line_type"] in MASS_LINES for lr in lines)

        items = []
        if not theirs and ours["total_cents"]:
            items.append({"family": "UNINVOICED_COLLECTION", "entity_type": "collection", "entity_id": ours["pickup_id"],
                          "status": "CHECK", "euros_at_stake_cents": -ours["total_cents"], "confidence": "medium",
                          "reason": f"This pickup is not on the operator invoice for {period}; contract version "
                                    f"{vid} gives {eur(ours['total_cents'])} (estimate).",
                          "sources": {"our_amount": f"Contract version {vid}"}})
        else:
            items += self._line_items(ours, lines, grade_unknown)
        if pickup["status"] in LIFT_STATUSES:
            wi = self._weight_item(ours, billed)
            if wi:
                items.append(wi)

        no_data = has_mass and not ours["ticket"] and ours["device_kg"] is None
        statuses = {i["status"] for i in items}
        if "CHECK" in statuses:
            status = "CHECK"
        elif no_data or "NO_DATA" in statuses:
            status = "NO_DATA"
        elif "EXPLAINED" in statuses:
            status = "EXPLAINED"
        else:
            status = "MATCH"
        first = next((i for s in STATUS_ORDER for i in items if i["status"] == s), None)
        if status == "NO_DATA" and no_data and (not first or first["status"] != "NO_DATA"):
            reason = f"No weighbridge ticket and no device weight; billed weight {billed} kg cannot be checked."
        elif first:
            reason = first["reason"]
        else:
            reason = f"Every charge for this lift matches contract version {vid} within {self.s.tolerance_pct:g}%."
        action = self._action(status, items, lines, ours)
        lead = max((i for i in items if i["status"] != "EXPLAINED"), key=lambda i: abs(i["euros_at_stake_cents"]),
                   default=first)
        by_line = {ln["invoice_line_id"]: ln for ln in theirs}
        lead_line = by_line.get((lead or {}).get("entity_id"))
        weak = action == "REQUEST_TICKET"
        inv_ids = sorted({ln["invoice_id"] for ln in theirs})
        first_check = next((i for i in items if i["status"] != "EXPLAINED"), first)
        detail = (f"{first_check['reason']} Our estimate for this pickup is {eur(ours['total_cents'])} and the invoice "
                  f"shows {eur(op_total)}." if first_check else reason)
        weights = f" ({billed} kg billed, {w['kg']} kg our weight)" if billed is not None and w["kg"] is not None else ""
        what = (f"The invoice shows {eur(op_total)} for this pickup and our estimate is {eur(ours['total_cents'])}{weights}."
                if theirs else f"This pickup is not on the invoice; our estimate is {eur(ours['total_cents'])}.")
        conf = (first or {}).get("confidence", w["confidence"])
        row_why = self._row_why(ours, w, theirs, inv_ids, op_total, billed, reason, conf, period, lines, items)
        row_why["ours"] = self._should_why(ours, w, has_mass)
        lift_qty = sum(int(ln.get("quantity") or 1) for ln in ours["lines"] if ln["line_type"] == "LIFT_FEE") or 1
        billed_lifts = sum(1 for ln in theirs if ln["line_type"] == "LIFT_FEE")
        if has_mass and w["kg"] is not None:
            spread = f" ± {tonnes(w['range_kg'])}" if w["source"] == "device" and w["range_kg"] else ""
            ours_note = f"{tonnes(w['kg'])}{spread}, {WEIGHT_NOTE[w['source']]}"
        elif has_mass:
            ours_note = "No weight yet"
        else:
            ours_note = lifts(lift_qty, ", your contract")
        if not theirs:
            billed_note = "Not on the invoice"
        elif billed is not None:
            billed_note = f"{tonnes(billed)} billed"
        else:
            billed_note = lifts(billed_lifts, " billed")
        dev, tk = ours["device_kg"], (ours["ticket"] or {}).get("allocated_net_kg")
        subject = f"the {material_text(ours['material'])} pickup on {short_day(ours['service_date'])}"
        if has_mass and billed is not None:
            opening = f"{subject} is billed at {tonnes(billed)}."
        elif theirs:
            opening = f"{subject} is billed at {eur(op_total)} ({billed_note})."
        else:
            opening = f"{subject} is not on the invoice."
        if has_mass and tk is not None:
            same = dev is not None and abs(dev - tk) * 100 <= self.s.weight_tolerance_pct * max(tk, 1)
            tail = (", and our container scale shows the same." if same else
                    f", and our container scale shows {tonnes(dev)}." if dev is not None else ".")
            check = f"Your scale ticket for this pickup shows {tonnes(tk)}{tail}"
        elif has_mass and dev is not None:
            check = f"No scale ticket has been shared yet. Our container scale shows {tonnes(dev)}."
        else:
            check = f"Under our contract it should cost {eur(ours['total_cents'])} ({ours_note})."
        return {
            "ours_note": ours_note, "billed_note": billed_note,
            "dispute_message": dispute_message(inv_ids[0] if inv_ids else None, opening, check,
                                               op_total - ours["total_cents"]),
            "site_id": pickup.get("site_id"), "operator_id": pickup.get("operator_id"),
            "draft_question": None if action == "NONE" else draft(
                action, f"the {(ours['material'] or 'waste').replace('_', ' ')} pickup on {ours['service_date']}",
                ours["operator_job_ref"] or "not given", ", ".join(inv_ids) or "for this period", detail),
            "pickup_id": ours["pickup_id"], "date": ours["service_date"], "material": ours["material"],
            "contract_id": ours["contract_id"], "contract_version_id": vid, "device_id": ours["device_id"],
            "operator_job_ref": ours["operator_job_ref"], "pickup_status": pickup["status"],
            "invoice_ids": inv_ids, "match_by": theirs[0]["match_by"] if theirs else None,
            "ours": {"amount_cents": ours["total_cents"], "weight_kg": w["kg"], "weight_source": w["source"],
                     "range_kg": w["range_kg"], "confidence": w["confidence"], "lower_bound": ours["lower_bound"],
                     "estimate": True, "cost_per_t_cents": ours["summary"]["total_cost_cents_per_t"]},
            "operator": {"amount_cents": op_total, "billed_kg": billed},
            "device_kg": ours["device_kg"],
            "ticket_kg": (ours["ticket"] or {}).get("allocated_net_kg"),
            "ticket_id": (ours["ticket"] or {}).get("ticket_id"),
            "difference_cents": op_total - ours["total_cents"],
            "euros_at_stake_cents": op_total - ours["total_cents"],
            "status": status, "reason": reason,
            "evidence": "weak" if weak else "strong",
            "suggested_action": action,
            "needs_attention": abs(op_total - ours["total_cents"]) > max(1, self._tol(max(abs(op_total), abs(ours["total_cents"])))),
            "short_reason": short_reason(lead),
            "dispute": {"invoice_id": inv_ids[0] if inv_ids else None,
                        "line_no": (lead_line or {}).get("line_no"),
                        "invoice_line_id": (lead_line or {}).get("invoice_line_id"), "operator_email": None},
            "cause": cause_of(first, status), "cause_text": CAUSE_TEXT.get(cause_of(first, status) or ""),
            "trail": {"pickup_id": ours["pickup_id"], "operator_job_ref": ours["operator_job_ref"],
                      "ticket_id": (ours["ticket"] or {}).get("ticket_id"), "contract_version_id": vid,
                      "invoice_ids": inv_ids,
                      "invoice_line_ids": [ln["invoice_line_id"] for ln in theirs if ln.get("invoice_line_id")],
                      "device_id": ours["device_id"]},
            "trigger_type": pickup.get("original_trigger_type") if pickup.get("trigger_type") == "RESCHEDULED"
            else pickup.get("trigger_type"),
            "explain": {"what": what, "why": reason, "how_sure": how_sure(conf, w)},
            "why": row_why,
            "fill_before_pct": pickup.get("device_fill_pct_before"),
            "summary": ours["summary"], "our_lines": ours["lines"], "price_args": ours["price_args"],
            "version": ours["version"], "weight_kg": w["kg"],
            "sources": {
                "our_amount": f"Contract version {vid}" if vid else None,
                "our_weight": WEIGHT_SOURCE[w["source"]].format(w["source_id"]) if w["source"] else "Not enough data",
                "operator_amount": f"Invoice {', '.join(inv_ids)}" if inv_ids else None,
                "billed_weight": f"Invoice item {tonnage['invoice_line_id']}" if tonnage else None,
                "device_weight": f"Device {ours['device_id']} estimate" if ours["device_kg"] is not None else None,
                "grade": f"Quality assessment {ours['grade_source']}" if ours["grade_source"] else
                ("Not shared (grade A assumed)" if ours["price_args"]["credit_eligible"] else None),
            },
            "items": items, "lines": lines if (theirs or ours["lines"]) else [],
        }
