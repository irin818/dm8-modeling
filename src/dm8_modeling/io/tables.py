"""Save small derived JSON/CSV summaries outside immutable raw directories."""
from __future__ import annotations
import csv
import json
from pathlib import Path


def save_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return path


def save_csv(path: Path, rows: list[dict]) -> Path:
    if not rows:
        raise ValueError("Cannot write an empty scientific summary table")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
