import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controllers.deps import unscoped

METRICS = ["n_operator_jobs", "n_completed_lifts", "on_time_rate", "missed_visit_rate", "weighbridge_shared_7d_rate",
           "median_share_lag_days", "billing_overcharge_pct", "billing_undercharge_pct", "discrepant_line_rate",
           "weight_bias_pct", "median_order_to_lift_hours"]


def export(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    rows = unscoped().scorecard.scorecard_rows()
    with (out / "my_scorecard.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["operator_id", "region_code", "month"] + METRICS)
        for r in rows:
            w.writerow([r["operator_id"], r["region_code"], r["month"]] +
                       ["" if r[m] is None else round(r[m], 4) for m in METRICS])
    return len(rows)


if __name__ == "__main__":
    print(export(Path(sys.argv[1] if len(sys.argv) > 1 else "api/exports")), "scorecard rows")
