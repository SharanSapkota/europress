import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import ASCENDING

from app.core.db import get_db

DATE_COLUMN = re.compile(r"(_at|_on|_from|_to|date|month)$")
TEXT_COLUMN = re.compile(r"(_id|_ref|_code|_weekdays|_mon_sun|_hours_local|^billing_period)$")
TS = re.compile(r"^\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(\.\d+)?(\+00(:00)?|Z)?$")
DAY = re.compile(r"^\d{4}-\d\d-\d\d$")
MONTH = re.compile(r"^\d{4}-\d\d$")
INT = re.compile(r"^-?\d+$")
FLOAT = re.compile(r"^-?\d*\.\d+$")
NULLS = {"", "NA", "null"}
INDEX_FIELDS = ["operator_job_ref", "device_id", "contract_id", "collection_id", "ticket_id", "invoice_id",
                "site_id", "customer_id", "operator_id"]
COMPOUND = {"telemetry_hourly": [("device_id", ASCENDING), ("measured_at", ASCENDING)]}


def parse_date(raw: str) -> datetime | None:
    if TS.match(raw):
        base = raw.replace("T", " ").replace("Z", "").split("+")[0]
        fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in base else "%Y-%m-%d %H:%M:%S"
        return datetime.strptime(base, fmt).replace(tzinfo=timezone.utc)
    if DAY.match(raw):
        return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if MONTH.match(raw):
        return datetime.strptime(raw, "%Y-%m").replace(tzinfo=timezone.utc)
    return None


def parse_value(key: str, raw: str):
    if raw in NULLS:
        return None
    if DATE_COLUMN.search(key) and (d := parse_date(raw)):
        return d
    if TEXT_COLUMN.search(key):
        return raw
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    if INT.match(raw):
        return int(raw)
    if FLOAT.match(raw):
        return float(raw)
    return raw


def collection_name(path: Path, root: Path) -> str:
    return "_".join(path.relative_to(root).with_suffix("").parts)


def read_csv(path: Path, root: Path | None = None) -> list[dict]:
    source = str(path.relative_to(root)) if root else path.name
    with path.open(newline="", encoding="utf-8") as f:
        return [{**{k: parse_value(k, v) for k, v in r.items()}, "_source_file": source} for r in csv.DictReader(f)]


def csv_files(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*.csv")):
        parts = path.relative_to(root).parts
        if path.name.startswith("labels_dev") or "labels_dev" in parts:
            print(f"WARNING skipped answer-key file {path.relative_to(root)}")
            continue
        if "benchmark" in parts:
            print(f"WARNING skipped evaluator-only file {path.relative_to(root)}")
            continue
        files.append(path)
    return files


def seed(root: Path, db) -> dict[str, int]:
    counts = {}
    for path in csv_files(root):
        name = collection_name(path, root)
        docs = read_csv(path, root)
        db.drop_collection(name)
        if docs:
            db[name].insert_many(docs)
            fields = set().union(*(d.keys() for d in docs))
            for field in INDEX_FIELDS:
                if field in fields:
                    db[name].create_index(field)
            if name in COMPOUND:
                db[name].create_index(COMPOUND[name])
        counts[name] = len(docs)
        print(f"{name:32} {len(docs)}")
    return counts


if __name__ == "__main__":
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/quickstart/public/csv")
    counts = seed(folder, get_db())
    print(f"{'total':32} {sum(counts.values())}")
