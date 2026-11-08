from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["MATCH", "CHECK", "EXPLAINED", "NO_DATA", "DISPUTED"]
Action = Literal["CORRECT_LINE", "REQUEST_TICKET", "NONE"]
Decision = Literal["ok", "dispute_draft", "dispute_sent"]
View = Literal["check", "disputed", "explained", "match"]


class Why(BaseModel):
    what: str
    source: str
    confidence: Literal["high", "medium", "low", "not enough data"]
    reason: str | None = None
    evidence: Literal["observed", "estimated", "simulated", "hypothetical"]


class DisputeRef(BaseModel):
    invoice_id: str | None
    line_no: int | None
    invoice_line_id: str | None
    operator_email: str | None


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
    needs_attention: bool
    short_reason: str | None
    dispute: DisputeRef
    found_status: Status
    decision: Decision | None = None
    decision_id: str | None = None
    decided_at: str | None = None
    disputed_at: str | None = None
    service_date: str | None
    operator_job_ref: str | None
    view: View
    ours_note: str
    billed_note: str
    dispute_message: str


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
    needs_attention: bool
    short_reason: str | None
    dispute: DisputeRef
    found_status: Status
    sources: dict[str, str | None]
    items: list[Item]
    lines: list[LineComparison]
    decision: Decision | None = None
    decision_id: str | None = None
    decided_at: str | None = None
    disputed_at: str | None = None
    view: View
    ours_note: str
    billed_note: str
    dispute_message: str


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
    attention_count: int
    match_count: int
    totals: Totals
    counts: dict[Status, int]
    view_counts: dict[View, int]
    line_counts: dict[Literal["MATCHED", "DUPLICATE", "NO_LIFT"], int]
    unmatched_lines: list[UnmatchedLine]
    rows: list[PickupComparison]
    why: dict[str, Why]


class DecisionIn(BaseModel):
    decision: Literal["ok", "question", "dispute_draft", "dispute_sent"]
    message: str | None = Field(None, max_length=4000)


class DecisionEntry(BaseModel):
    decision_id: str
    item_type: Literal["invoice_item", "operator", "feature"]
    item_id: str
    label: str
    decision: Literal["ok", "question", "dispute_draft", "dispute_sent", "prepare", "approve", "not_now", "undo"]
    suggestion: dict[str, str | None]
    numbers: dict[str, str | int | float | None]
    undoes: str | None
    created_at: str
    user: str
    evidence: dict[str, str | int | float | None] | None = None
    message: str | None = None


class TrailBox(BaseModel):
    label: str
    value: str


class HistoryEntry(DecisionEntry):
    text: str
    undone: bool
    title: str
    detail: str
    suggestion_text: str
    chip: str
    chip_tone: Literal["check", "good", "neutral", "blue", "disputed"]
    trail: list[TrailBox]


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
    site_label: str | None
    short_reason: str | None
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


class CostHighlight(BaseModel):
    ratio: float
    sentence: str
    reason: str | None
    device_id: str


class CostsResponse(BaseModel):
    customer_id: str | None
    customer_name: str | None
    site_names: list[str]
    months: int
    periods: list[str]
    headline: str
    highlight: CostHighlight | None
    site_count: int
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
    request_draft: str | None = None
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
    message: str | None = Field(None, max_length=4000)


class OperatorDecisionOut(DecisionEntry):
    operator_id: str
    action: str
    draft: str | None


Tag = Literal["OBSERVED", "ESTIMATED", "SIMULATED", "HYPOTHETICAL"]


class Figure(BaseModel):
    label: str
    value: str | int | float | None
    unit: str
    tag: Tag
    range: str | None


class Bar(BaseModel):
    label: str
    value: float
    unit: str
    tag: Tag


class CardExample(BaseModel):
    site: str | None
    device: str | None
    numbers: list[Figure]
    bars: list[Bar]
    result: str


class CardEvidence(BaseModel):
    tag: Tag
    range: str | None
    confidence: Literal["High", "Medium", "Low"]
    pickups_used: int
    data_used: str
    neutrality_note: str
    draft_note: str


class Reasoning(BaseModel):
    title: str
    text: str


class Advanced(BaseModel):
    formula: str
    columns: list[str]
    rows: list[list[str | int | float | None]]


class DetailBar(BaseModel):
    value: float
    max: float


class DetailRow(BaseModel):
    date: str | None
    label: str
    bar: DetailBar | None
    bar_text: str
    note: str
    tone: Literal["check", "muted"]
    value: int | None
    unit: str


class CardDetails(BaseModel):
    summary: str
    info: str
    columns: list[str]
    rows: list[DetailRow]


class FeatureCard(BaseModel):
    id: str
    title: str
    subtitle: str
    status: Literal["Check this", "Worth a check", "Good", "Not enough data"]
    explanation: str
    reasoning: list[Reasoning]
    example: CardExample | None
    evidence: CardEvidence
    actions: list[Literal["prepare", "not_now", "undo"]]
    advanced: Advanced
    details: CardDetails
    decision: Literal["prepare", "not_now"] | None
    decision_id: str | None
    decided_at: str | None
    headline: str
    example_line: str
    value_cents: int
    rank: int


class CardsResponse(BaseModel):
    customer_id: str
    cards: list[FeatureCard]


class FeatureDecisionIn(BaseModel):
    decision: Literal["prepare", "not_now"]


class Tile(BaseModel):
    key: str
    label: str
    value: int | float | None
    unit: str
    signed: bool
    status: Literal["OK", "CHECK"]
    link: str


class NextDecision(BaseModel):
    id: str
    sentence: str
    estimate: str
    link: str
    value_cents: int


class DashboardResponse(BaseModel):
    customer_id: str
    customer_name: str | None
    sites: list[Option]
    operator_count: int
    period: str | None
    periods: list[str]
    totals: Totals | None
    why: dict[str, Why]
    tiles: list[Tile]
    next_decision: NextDecision | None


class FillBar(BaseModel):
    now_kg: float
    target_kg: int


class SensorNote(BaseModel):
    text: str
    since: str


class ContainerCard(BaseModel):
    id: str
    kind: Literal["rule", "sensor"]
    device_id: str
    material: str
    site: str
    old_rule: str
    new_rule: str | None
    estimate: str | None
    estimate_note: str | None
    value_cents: int
    fill: FillBar | None
    sensor: SensorNote | None
    highlight: bool
    why: Why | None
    decision: str | None


class ContainersResponse(BaseModel):
    customer_id: str
    months: int
    cards: list[ContainerCard]


class ContainerDecisionIn(BaseModel):
    decision: Literal["approve", "not_now", "prepare"]


class Plan(BaseModel):
    key: str
    name: str
    price_eur: float | None
    current: bool
    features: list[str]


class EuropressView(BaseModel):
    adoption_pct: float
    containers: int
    yearly_eur: int
    text: str


class ValueResponse(BaseModel):
    customer_id: str
    months: int
    devices: int
    value_found_cents: int
    plan_cost_cents: int
    net_cents: int
    why: dict[str, Why]
    plans: list[Plan]
    europress: EuropressView
