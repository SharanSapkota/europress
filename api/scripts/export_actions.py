import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.controllers.deps import unscoped

CASES = Path(__file__).resolve().parents[2] / "data" / "quickstart" / "public" / "csv" / "benchmark" / "operator_action_cases.csv"


def read_cases(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(r, as_of_at=r["as_of_at"].replace(" ", "T").replace("+00", "Z")) for r in csv.DictReader(f)]


def export(out: Path, cases: Path = CASES) -> int:
    out.mkdir(parents=True, exist_ok=True)
    chosen = unscoped().actions.cases(read_cases(cases))
    with (out / "my_actions.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "actions"])
        for c in chosen:
            w.writerow([c["case_id"], c["actions"]])
    return len(chosen)


if __name__ == "__main__":
    print(export(Path(sys.argv[1] if len(sys.argv) > 1 else "api/exports")), "action cases")
