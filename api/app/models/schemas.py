from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["MATCH", "CHECK", "EXPLAINED", "NO_DATA", "DISPUTED"]
Action = Literal["CORRECT_LINE", "REQUEST_TICKET", "NONE"]
Decision = Literal["ok", "dispute_draft", "dispute_sent"]


class Why(BaseModel):
    what: str
    source: str
    confidence: Literal["high", "low", "not enough data"]
    reason: str | None = None
    evidence: Literal["observed", "estimated", "simulated", "hypothetical"]


class Trail(BaseModel):
    pickup_id: str | None = None
    operator_job_ref: str | None = None
    ticket_id: str | None = None
    contract_version_id: str | None = None
    invoice_ids: list[str] = []
    invoice_line_ids: list[str] = []
    device_id: str | None = None


class Explain(BaseModel):
    what: str
    why: str
    how_sure: str


class LinePart(BaseModel):
    quantity: float | None
    unit: str | None
    rate_cents: int | None
    amount_cents: int


class LineComparison(BaseModel):
    line_type: str
    label: str
    ours: LinePart | None
    operator: LinePart | None
    difference_cents: int
    duplicate: bool
    status: Literal["MATCH", "CHECK"]
    our_source: str | None
    operator_source: str | None
    invoice_line_id: str | None
    why: Why


class Item(BaseModel):
    family: str
    entity_type: Literal["collection", "invoice_line"]
    entity_id: str | None
    status: Status
    euros_at_stake_cents: int
    confidence: str
    reason: str
    sources: dict[str, str | None]
    line_type: str | None = None


class UnmatchedLine(Item):
    label: str
    draft_question: str
    invoice_id: str
    operator_id: str | None
    suggested_action: Action
    explain: Explain
    why: dict[str, Why]
    cause: str
    cause_text: str
    trail: Trail
    found_status: Status
    decision: Decision | None = None
    decision_id: str | None = None
    decided_at: str | None = None
    disputed_at: str | None = None
    service_date: str | None
    operator_job_ref: str | None


class OurSide(BaseModel):
    amount_cents: int
    weight_kg: int | None
    weight_source: Literal["ticket", "invoice", "device"] | None
    range_kg: int | None
    confidence: str
    lower_bound: bool
    estimate: bool
    cost_per_t_cents: int | None


class OperatorSide(BaseModel):
    amount_cents: int
    billed_kg: int | None


class PickupComparison(BaseModel):
    pickup_id: str
    site_id: str | None
    operator_id: str | None
    draft_question: str | None
    date: str | None
    material: str | None
    contract_id: str
    contract_version_id: str | None
    device_id: str
    operator_job_ref: str | None
    pickup_status: str
    invoice_ids: list[str]
    match_by: Literal["job_ref", "contract_date_type"] | None
    ours: OurSide
    operator: OperatorSide
    device_kg: int | None
    ticket_kg: int | None
    difference_cents: int
    euros_at_stake_cents: int
    status: Status
    reason: str
    evidence: Literal["strong", "weak"]
    suggested_action: Action
    explain: Explain
    why: dict[str, Why]
    cause: str | None
    cause_text: str | None
    trail: Trail
    found_status: Status
    sources: dict[str, str | None]
    items: list[Item]
    lines: list[LineComparison]
    decision: Decision | None = None
    decision_id: str | None = None
    decided_at: str | None = None
    disputed_at: str | None = None


class Totals(BaseModel):
    ours_cents: int
    operator_cents: int
    difference_cents: int
    unmatched_cents: int
    monthly_fixed_cents: int


class ComparisonResponse(BaseModel):
    period: str
    tolerance_pct: float
    customer_id: str | None
    customer_name: str | None
    site_ids: list[str]
    site_names: list[str]
    operator_ids: list[str]
    operator_names: list[str]
    line_total: int
    totals: Totals
    counts: dict[Status, int]
    line_counts: dict[Literal["MATCHED", "DUPLICATE", "NO_LIFT"], int]
    unmatched_lines: list[UnmatchedLine]
    rows: list[PickupComparison]
    why: dict[str, Why]


class DecisionIn(BaseModel):
    decision: Decision


class DecisionEntry(BaseModel):
    decision_id: str
    item_type: Literal["invoice_item", "operator"]
    item_id: str
    label: str
    decision: Literal["ok", "dispute_draft", "dispute_sent", "prepare", "not_now", "undo"]
    suggestion: dict[str, str | None]
    numbers: dict[str, str | int | float | None]
    undoes: str | None
    created_at: str
    user: str


class HistoryEntry(DecisionEntry):
    text: str
    undone: bool


class WeightSources(BaseModel):
    ticket: int
    invoice: int
    device: int


class Breakdown(BaseModel):
    pickup_fees_cents: int
    weight_fees_cents: int
    other_charges_cents: int
    material_credit_cents: int


class Constraints(BaseModel):
    max_days: int | None
    low_fill_pickups: int
    required_low_fill_pickups: int
    hours_full: int | None
    valid_reading_pct: int | None
    pickups_without_ticket: int | None


class Container(BaseModel):
    device_id: str
    contract_id: str
    material: str | None
    name: str
    full_name: str
    site_name: str | None
    cost_per_t_cents: int | None
    benchmark_cents_per_t: int | None
    ratio: float | None
    ratio_label: str | None
    status: Literal["CHECK", "NORMAL"]
    pickups: int
    pickups_with_weight: int
    confidence: Literal["sure", "not sure yet"]
    breakdown: Breakdown
    estimate: bool
    main_reason: str
    weight_sources: WeightSources
    sources_text: str
    contract_version_id: str | None
    constraints: Constraints
    why: dict[str, Why]


class CostsResponse(BaseModel):
    customer_id: str | None
    customer_name: str | None
    site_names: list[str]
    months: int
    periods: list[str]
    headline: str
    containers: list[Container]


class Measure(BaseModel):
    key: str
    label: str
    value: str
    status: Literal["GOOD", "CHECK"]
    source: str
    why: Why


class OperatorCard(BaseModel):
    operator_id: str
    name: str
    materials: list[str]
    pickups: int
    months: int
    months_covered: list[str]
    enough_data: bool
    measures: list[Measure]
    status: Literal["GOOD", "CHECK"]
    persistent_checks: list[str]
    suggested_action: Literal["NONE", "REQUEST_TICKETS", "CORRECT_LINES", "RENEGOTIATE", "TENDER"]
    suggestion: str
    why: str
    value_cents: int | None
    value_is_estimate: bool
    draft: str | None
    decision: Literal["prepare", "not_now"] | None
    decision_id: str | None
    decided_at: str | None
    suggestion_why: Why


class Option(BaseModel):
    id: str
    name: str


class FilterOptions(BaseModel):
    customers: list[Option]
    sites: list[Option]
    operators: list[Option]
    months: list[str]


class OperatorFilters(BaseModel):
    customer_id: str | None
    site_id: str | None
    period: str
    from_: str | None = Field(None, alias="from", serialization_alias="from")
    to: str | None
    operator_id: str | None

    model_config = {"populate_by_name": True}


class OperatorsResponse(BaseModel):
    customer_id: str | None
    customer_name: str | None
    filters: OperatorFilters
    options: FilterOptions
    months: int
    periods: list[str]
    on_time_window_hours: float
    operators: list[OperatorCard]


class OperatorDecisionIn(BaseModel):
    decision: Literal["prepare", "not_now"]


class OperatorDecisionOut(DecisionEntry):
    operator_id: str
    action: str
    draft: str | None
