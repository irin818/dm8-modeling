"""Exploratory control: test whether a pixel adds signal beyond peer ROI drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from dm8_modeling.data import align_session, discover_sessions
from dm8_modeling.model import _scores, lagged_design
from dm8_modeling.pixel import _fit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=Path("outputs/pixel_raw"))
    args = parser.parse_args()
    reports = []
    for session in discover_sessions(args.data_root):
        path = args.results_dir / session.fly / session.run_id / "pixel_metrics.json"
        report = json.loads(path.read_text())
        aligned = align_session(session)
        lag = int(report["lag_count"])
        eligible = aligned.update_index >= lag - 1
        y = aligned.response[eligible].astype(float)
        design = lagged_design(aligned.stimulus, aligned.update_index[eligible], lag)
        train_end = report["train_frames"]
        validation_start = train_end + report["purge_frames_each"]
        validation_end = validation_start + report["validation_frames"]
        test_start = validation_end + report["purge_frames_each"]
        if len(y) != report["eligible_frames"] or len(y) - test_start != report["test_frames"]:
            raise ValueError(f"Saved split differs from source data for {session.fly}")
        fit_rows = np.r_[0:train_end, validation_start:validation_end]
        rows = []
        for roi, entry in enumerate(report["roi_metrics"]):
            if len(aligned.roi_labels) < 2:
                raise ValueError("Peer-ROI control requires at least two ROIs")
            peer_median = np.median(np.delete(y, roi, axis=1), axis=1)
            peer_sd = float(peer_median[fit_rows].std())
            if peer_sd == 0:
                raise ValueError(f"Constant peer-ROI median for {session.fly}/{entry['roi']}")
            peer = ((peer_median - peer_median[fit_rows].mean()) / peer_sd)[:, None]
            pixel = entry["pixel_row_zero_based"] * 15 + entry["pixel_col_zero_based"]
            columns = np.arange(lag) * aligned.stimulus.shape[1] + pixel
            pixel_history = design[:, columns].astype(float)
            target = y[:, roi]
            penalty = float(entry["selected_penalty"])
            peer_beta, peer_intercept = _fit(peer[fit_rows], target[fit_rows], penalty)
            both = np.column_stack([pixel_history, peer])
            both_beta, both_intercept = _fit(both[fit_rows], target[fit_rows], penalty)
            peer_pred = peer[test_start:] @ peer_beta + peer_intercept
            both_pred = both[test_start:] @ both_beta + both_intercept
            peer_r2 = float(_scores(target[test_start:, None], peer_pred[:, None])[1][0])
            both_r2 = float(_scores(target[test_start:, None], both_pred[:, None])[1][0])
            rows.append({"roi": entry["roi"], "pixel_only_test_r2": entry["test_r2"],
                         "peer_median_test_r2": peer_r2, "pixel_plus_peer_test_r2": both_r2,
                         "incremental_r2_over_peer_median": both_r2 - peer_r2})
        reports.append({"fly": session.fly, "run_id": session.run_id, "roi_metrics": rows})
    output = {
        "method": "exploratory_leave_target_out_peer_median_control",
        "note": "Peer median uses same-time test responses of other ROIs. It is an artifact/common-signal diagnostic, not a deployable stimulus-only encoding model. It was defined after inspecting earlier test results.",
        "sessions": reports,
    }
    destination = args.results_dir / "common_mode_control.json"
    destination.write_text(json.dumps(output, indent=2, allow_nan=False))
    for report in reports:
        print(report["fly"], [(r["roi"], round(r["incremental_r2_over_peer_median"], 3))
                              for r in report["roi_metrics"] if r["roi"] in {"Mean29", "Mean34", "Mean36"}])
    print(destination)


if __name__ == "__main__":
    main()
