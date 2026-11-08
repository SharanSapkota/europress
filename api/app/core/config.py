import os
from dataclasses import dataclass
from pathlib import Path


def load_env(path: Path = Path(__file__).resolve().parents[3] / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("DATABASE_URL") or os.getenv("MONGO_URI") or "mongodb://localhost:27017/portal"
    database_name: str = os.getenv("DATABASE_NAME") or "portal"
    local_tz: str = "Europe/Helsinki"
    tolerance_pct: float = float(os.getenv("TOLERANCE_PCT", "2"))
    weight_tolerance_pct: float = float(os.getenv("WEIGHT_TOLERANCE_PCT", "10"))
    device_range_pct: float = float(os.getenv("DEVICE_RANGE_PCT", "3.3"))
    stored_tare_explains: bool = os.getenv("STORED_TARE_EXPLAINS", "false").lower() == "true"
    user: str = os.getenv("PORTAL_USER") or "demo user"
    customer_id: str | None = os.getenv("CURRENT_CUSTOMER_ID") or os.getenv("CUSTOMER_ID") or None
    sure_min_pickups: int = int(os.getenv("SURE_MIN_PICKUPS", "10"))
    low_fill_pct: float = float(os.getenv("LOW_FILL_PCT", "50"))
    cost_ratio_check: float = float(os.getenv("COST_RATIO_CHECK", "1.2"))
    on_time_window_hours: float = float(os.getenv("ON_TIME_WINDOW_HOURS", "2"))
    billing_accuracy_min: float = float(os.getenv("BILLING_ACCURACY_MIN", "98"))
    on_time_min: float = float(os.getenv("ON_TIME_MIN", "0.9"))
    missed_visits_max: int = int(os.getenv("MISSED_VISITS_MAX", "1"))
    tickets_shared_min: float = float(os.getenv("TICKETS_SHARED_MIN", "0.8"))
    share_lag_max_days: float = float(os.getenv("SHARE_LAG_MAX_DAYS", "7"))
    lines_check_max: float = float(os.getenv("LINES_CHECK_MAX", "0.05"))
    weight_gap_max_pct: float = float(os.getenv("WEIGHT_GAP_MAX_PCT", "3"))
    pattern_months: int = int(os.getenv("PATTERN_MONTHS", "3"))
    dispute_lookback_days: int = 90
    dispute_recovery_rate: float = 0.9
    dispute_admin_cost_cents: int = 6000
    request_comply_prob: float = 0.6
    request_admin_cost_cents: int = 2000
    renegotiation_success_prob: float = 0.5
    renegotiation_min_gap_pct: float = 10
    renegotiation_effort_cents: int = 15000
    tender_success_prob: float = 0.8
    tender_min_gap_pct: float = 10
    tender_switch_cost_cents: int = 50000
    valuation_horizon_months: int = 12


settings = Settings()
