"""Small append-only index of completed Phase 5 experiment artifacts."""

from __future__ import annotations

import csv
from pathlib import Path


FIELDS = ("experiment_id", "date_utc", "dataset", "fold", "model", "response_kind",
          "normalization", "hyperparameters", "roi_count", "all_roi_median_r2",
          "responsive_median_r2", "fraction_positive_r2", "comparison_baseline",
          "notes", "artifact_dir")


def write_registry(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FIELDS} for row in rows)
    return path
