"""Fit and compare a compact CNN with the saved interpretable pixel model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from .models.neural.compact_cnn import fit_compact_cnn
from .data import align_session, discover_sessions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--baseline-dir", type=Path, default=Path("outputs/pixel_raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/cnn_comparison"))
    parser.add_argument("--max-epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=20260929)
    args = parser.parse_args()

    summaries = []
    for session in discover_sessions(args.data_root):
        print(f"Comparing {session.fly}/{session.run_id}...", flush=True)
        aligned = align_session(session)
        baseline_dir = args.baseline_dir / session.fly / session.run_id
        with (baseline_dir / "pixel_metrics.json").open() as handle:
            baseline_report = json.load(handle)
        with np.load(baseline_dir / "pixel_model.npz", allow_pickle=False) as saved:
            baseline_model = {key: saved[key] for key in saved.files}
        if str(baseline_model["fly"]) != session.fly or str(baseline_model["run_id"]) != session.run_id:
            raise ValueError(f"Baseline session identity differs: {baseline_dir}")
        if json.loads(str(baseline_model["source_sha256_json"])) != aligned.qc["source_sha256"]:
            raise ValueError(f"Baseline source files changed: {baseline_dir}")
        if int(baseline_model["lag_count"]) != baseline_report["lag_count"]:
            raise ValueError(f"Baseline lag count differs: {baseline_dir}")
        result = fit_compact_cnn(
            aligned, baseline_report, baseline_model,
            max_epochs=args.max_epochs, patience=args.patience,
            batch_size=args.batch_size, learning_rate=args.learning_rate,
            weight_decay=args.weight_decay, seed=args.seed,
        )
        result.report["source_sha256"] = aligned.qc["source_sha256"]
        output = args.output_dir / session.fly / session.run_id
        output.mkdir(parents=True, exist_ok=True)
        with (output / "cnn_metrics.json").open("w") as handle:
            json.dump(result.report, handle, indent=2, ensure_ascii=False, allow_nan=False)
        np.savez_compressed(
            output / "cnn_test_predictions.npz",
            test_actual=result.test_actual,
            test_cnn_predicted=result.test_predicted,
            test_pixel_predicted=result.test_baseline_predicted,
            test_time_us=result.test_time_us,
            roi_labels=np.asarray(aligned.roi_labels),
        )
        torch.save({
            "state_dict": result.model_state,
            "fly": session.fly,
            "run_id": session.run_id,
            "lag_count": result.report["lag_count"],
            "test_start_eligible_frame": baseline_report["eligible_frames"] - baseline_report["test_frames"],
            "roi_labels": aligned.roi_labels,
            "selected_pixels": baseline_model["selected_pixels"].tolist(),
            "fit_mean": result.report["fit_mean"],
            "fit_sd": result.report["fit_sd"],
            "source_sha256": aligned.qc["source_sha256"],
        }, output / "cnn_model.pt")
        summary = {key: value for key, value in result.report.items()
                   if key not in {"roi_metrics", "training_curve", "baseline_train_selected_pixels", "source_sha256", "fit_mean", "fit_sd"}}
        summaries.append(summary)
        print(f"  epoch {summary['selected_epoch']}; median test R²: pixel {summary['median_pixel_test_r2']:.3f}, CNN {summary['median_cnn_test_r2']:.3f}; ΔR² > 0.01 in {summary['roi_cnn_better_by_0p01_r2_count']}/{len(aligned.roi_labels)} ROIs", flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "summary.json").open("w") as handle:
        json.dump(summaries, handle, indent=2, ensure_ascii=False, allow_nan=False)


if __name__ == "__main__":
    main()
