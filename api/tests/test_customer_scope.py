import json
import re
from functools import lru_cache

import pytest
from fakes import base_repos, services
from fastapi import HTTPException

from app.controllers.deps import resolve_scope

A, B = "ORG-0001", "ORG-0004"


@lru_cache
def ids_of(customer: str) -> set[str]:
    base = base_repos()
    out = set()
    for name, field in (("devices", "device_id"), ("sites", "site_id"), ("pickups", "collection_id"),
                        ("contracts", "contract_id"), ("invoices", "invoice_id")):
        out |= {d[field] for d in base[name].all() if d.get("customer_id") == customer}
    return out


def everything(svc) -> str:
    cid = svc.customer_id
    parts = [svc.comparison.compare(p, cid) for p in svc.comparison.periods()]
    operators = dict(svc.scorecard.operators(customer_id=cid, site_id=svc.site_id), options=None)
    dashboard = dict(svc.dashboard.dashboard(cid), sites=None)
    parts += [svc.costs.costs(customer_id=cid), operators, svc.pickups.cards(cid), svc.site_checks.cards(cid),
              svc.fleet.cards(cid), svc.value.summary(cid), dashboard]
    return json.dumps(parts, default=str)


@lru_cache
def tokens(customer: str, site: str | None = None) -> set[str]:
    return set(re.findall(r"[A-Z]{2,4}-[0-9A-Z-]+", everything(services(customer, site))))


def test_customer_a_never_sees_customer_b():
    seen = tokens(A)
    assert seen & ids_of(A)
    assert not seen & ids_of(B)


def test_customer_b_never_sees_customer_a():
    assert not tokens(B) & ids_of(A)


def test_site_scope_keeps_one_site():
    site = sorted(s for s in ids_of(A) if s.startswith("SITE-"))[0]
    other_sites = {s for s in ids_of(A) if s.startswith("SITE-")} - {site}
    svc = services(A, site)
    devices = {d["device_id"] for d in svc.r["devices"].all()}
    assert devices and all(d["site_id"] == site for d in svc.r["devices"].all())
    assert not tokens(A, site) & other_sites
    assert {s["site_id"] for s in svc.r["customer_sites"].all()} == {s for s in ids_of(A) if s.startswith("SITE-")}


def test_other_customers_site_or_unknown_customer_is_404():
    base = base_repos()
    b_site = next(s for s in ids_of(B) if s.startswith("SITE-"))
    with pytest.raises(HTTPException) as e:
        resolve_scope(A, b_site, base)
    assert e.value.status_code == 404
    with pytest.raises(HTTPException):
        resolve_scope("ORG-NONE", None, base)
    assert resolve_scope(A, None, base).customer_id == A


def test_other_customers_pickup_invoice_and_decision_are_not_found():
    svc_a, svc_b = services(A), services(B)
    b_pickup = next(i for i in ids_of(B) if i.startswith("COL-"))
    assert svc_a.comparison.detail(b_pickup) is None
    assert svc_a.comparison.decide(b_pickup, "ok") is None
    b_line = next(ln["invoice_line_id"] for ln in svc_b.r["lines"].all())
    assert svc_a.comparison.decide(b_line, "ok") is None
    entry = svc_b.decisions.record("operator", "OP-A", "prepare", "x", {"action": "NONE"}, {})
    svc_a.decisions.repo.repo.entries.append(dict(entry, _id=entry["decision_id"]))
    assert svc_a.decisions.undo(entry["decision_id"]) is None and svc_a.decisions.history(3) == []


def test_customer_view_has_no_peer_valuation():
    svc = services(A)
    assert svc.actions is None
    assert all(c["value_cents"] is None for c in svc.scorecard.operators(customer_id=A)["operators"])
