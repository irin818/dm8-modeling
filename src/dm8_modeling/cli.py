"""Command-line entry point for read-only experimental-data analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .data import align_session, discover_sessions
from .model import fit_sta_baseline
from .ridge import fit_binned_ridge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True, help="Dm8_module or UV-15Hz directory")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/first_pass"))
    parser.add_argument("--lag-count", type=int, default=45, help="Number of past 15 Hz updates, including current")
    parser.add_argument("--model", choices=["sta", "ridge"], default="sta")
    parser.add_argument("--response-transform", choices=["raw", "causal_ema_60s"], default="raw")
    parser.add_argument("--qc-only", action="store_true", help="Validate and summarize inputs without fitting")
    args = parser.parse_args()
    sessions = discover_sessions(args.data_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    for session in sessions:
        print(f"Checking {session.fly}/{session.run_id}...", flush=True)
        aligned = align_session(session)
        session_output = args.output_dir / session.fly / session.run_id
        session_output.mkdir(parents=True, exist_ok=True)
        with (session_output / "data_qc.json").open("w") as handle:
            json.dump(aligned.qc, handle, indent=2, ensure_ascii=False)
        if args.qc_only:
            reports.append({"fly": session.fly, "run_id": session.run_id, "qc": aligned.qc})
            continue
        if args.model == "sta":
            print(f"Fitting causal STA for {len(aligned.roi_labels)} ROIs...", flush=True)
            result = fit_sta_baseline(aligned, lag_count=args.lag_count, response_transform=args.response_transform)
            np.savez_compressed(
                session_output / "baseline_kernels.npz",
                full_sta=result.sta,
                rank_one_sta=result.rank_one_sta,
                roi_labels=np.asarray(aligned.roi_labels),
            )
        else:
            print(f"Fitting binned ridge STRF for {len(aligned.roi_labels)} ROIs...", flush=True)
            result = fit_binned_ridge(aligned, response_transform=args.response_transform)
            np.savez_compressed(
                session_output / "ridge_coefficients.npz",
                coefficients=result.coefficients,
                roi_labels=np.asarray(aligned.roi_labels),
            )
        with (session_output / "baseline_metrics.json").open("w") as handle:
            json.dump(result.report, handle, indent=2, ensure_ascii=False, allow_nan=False)
        reports.append({key: value for key, value in result.report.items() if key != "roi_metrics"})
    with (args.output_dir / "summary.json").open("w") as handle:
        json.dump(reports, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps(reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
