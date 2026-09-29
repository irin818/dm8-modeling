"""Orchestrate read-only trace, clock and RF audits; write derived tables.

All outputs go outside the immutable Dm8_module source tree.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from ..data import _read_clock, _read_results, align_session, discover_sessions
from .diagnostics import _response_rows, _clock_summary
from .rf_quality import _rf_rows

def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No audit rows")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(data_root: Path, output_dir: Path, pixel_results_dir: Path | None = None) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    response_rows, rf_rows, candidate_rows, clocks = [], [], [], []
    for session in discover_sessions(data_root):
        response, labels = _read_results(session.path / "Results.csv")
        zeiss = _read_clock(next(session.path.glob("zeiss_ttl_*.csv")), "timestamp_us")
        locked = _read_clock(session.path / "analysis_marker_lock" / "dlp_ttl_marker_locked.csv", "timestamp_us")
        assert len(response) == len(zeiss)
        response_rows.extend(_response_rows(session.fly, session.run_id, response, labels, 1e6 / np.median(np.diff(zeiss))))
        clocks.append({"fly": session.fly, "run_id": session.run_id, **_clock_summary("zeiss_frame_out", zeiss, None)})
        clocks.append({"fly": session.fly, "run_id": session.run_id, **_clock_summary("marker_locked_DLP", locked, 1e6 / 120)})
        pixel_path = (pixel_results_dir / session.fly / session.run_id / "pixel_metrics.json") if pixel_results_dir else None
        pixel = json.loads(pixel_path.read_text()) if pixel_path and pixel_path.is_file() else None
        rr, cc = _rf_rows(align_session(session), pixel)
        rf_rows.extend(rr)
        candidate_rows.extend(cc)
        print(session.fly, len(labels), "ROIs audited", flush=True)
    _write_csv(output_dir / "roi_quality.csv", response_rows)
    _write_csv(output_dir / "rf_quality.csv", rf_rows)
    _write_csv(output_dir / "candidate_preprocessing.csv", candidate_rows)
    summary = {"response_roi_count": len(response_rows), "rf_roi_count": len(rf_rows),
               "clocks": clocks, "rf_confidence_counts": {name: sum(row["rf_confidence"] == name for row in rf_rows)
                   for name in ("HIGH_CONFIDENCE_RESPONSIVE", "MODERATE_CONFIDENCE", "LOW_CONFIDENCE", "NO_DETECTABLE_RF")},
               "candidate_preprocessing": candidate_rows}
    (output_dir / "response_timing_rf_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pixel-results-dir", type=Path)
    args = parser.parse_args()
    summary = audit(args.data_root, args.output_dir, args.pixel_results_dir)
    print(summary["rf_confidence_counts"])
