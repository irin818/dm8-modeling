"""Command-line entry point for read-only experimental-data analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from ..data import align_session, discover_sessions
from ..rf.sta import fit_sta_baseline
from ..rf.null_tests import adjust_pixel_reports
from ..models.linear.pixel_temporal import fit_pixel_model
from ..models.linear.binned_strf import fit_binned_ridge
from ..workspace import WorkspacePaths, scan_data_inventory, write_inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd(), help="Root containing simulate and Dm8_module")
    parser.add_argument("--data-root", type=Path, help="Override Dm8_module or UV-15Hz directory")
    parser.add_argument("--stimulus-code-root", type=Path, help="Override the read-only simulate directory")
    parser.add_argument("--output-dir", type=Path, help="Derived outputs; defaults to outputs/first_pass or outputs/audit")
    parser.add_argument("--inventory", action="store_true", help="Write a metadata-only inventory of every experimental file")
    parser.add_argument("--audit", action="store_true", help="Audit ROI, timing and exploratory RF quality")
    parser.add_argument("--explain-session", metavar="FLY_OR_RUN", help="Explain one session's data lifecycle and assumptions")
    parser.add_argument("--pixel-results-dir", type=Path, help="Existing pixel metrics for audit confidence classification")
    parser.add_argument("--lag-count", type=int, default=None, help="Past 15 Hz updates; default 18 for pixel, 45 for STA")
    parser.add_argument("--model", choices=["sta", "ridge", "pixel"], default="sta")
    parser.add_argument("--response-transform", choices=["raw", "causal_ema_60s"], default="raw")
    parser.add_argument("--qc-only", action="store_true", help="Validate and summarize inputs without fitting")
    args = parser.parse_args()
    paths = WorkspacePaths.resolve(args.workspace_root, args.data_root, args.stimulus_code_root,
                                   args.output_dir or args.workspace_root / "outputs" / ("audit" if args.inventory or args.audit else "first_pass"))
    if args.inventory:
        entries = scan_data_inventory(paths.data_root)
        written = write_inventory(entries, paths.output_dir)
        print(f"Inventoried {len(entries)} files: {written[0]} and {written[1]}")
    if args.audit:
        from ..evaluation.audit import audit
        result = audit(paths.data_root, paths.output_dir,
                       args.pixel_results_dir or paths.root / "outputs" / "pixel_raw")
        print(json.dumps({"response_roi_count": result["response_roi_count"],
                          "rf_confidence_counts": result["rf_confidence_counts"]}, ensure_ascii=False))
    if args.inventory or args.audit:
        return
    if args.explain_session:
        sessions = discover_sessions(paths.data_root)
        matches = [s for s in sessions if args.explain_session in (s.fly, s.run_id, f"{s.fly}/{s.run_id}")]
        if len(matches) != 1:
            parser.error("--explain-session must identify exactly one fly or run")
        aligned = align_session(matches[0])
        print(json.dumps({
            "session": f"{matches[0].fly}/{matches[0].run_id}",
            "stimulus_source": str(paths.stimulus_code_root),
            "stimulus_package": str(matches[0].path / "stimulus_package" / "stim_realized.npz"),
            "stimulus_update_shape": list(aligned.stimulus.shape),
            "display_frames": aligned.qc["display_frames"],
            "display_timing": "marker-locked DLP TTL, microseconds",
            "imaging_timing": "Zeiss frame-out TTL proxy, microseconds",
            "response_file": str(matches[0].path / "Results.csv"),
            "response_kind": aligned.qc["response_kind"],
            "model_ready_y_shape": list(aligned.response.shape),
            "model_ready_X": "causal lagged windows of stimulus [frame, lag × 225]",
            "known_unknowns": ["exact June stimulus source revision", "ROI masks and raw imaging",
                               "official fluorescence preprocessing", "exposure onset", "wavelength and irradiance"],
        }, indent=2, ensure_ascii=False))
        return
    if args.model == "pixel" and args.response_transform != "raw":
        parser.error("The validated pixel model uses raw ROI intensity only")
    lag_count = args.lag_count if args.lag_count is not None else (18 if args.model == "pixel" else 45)
    sessions = discover_sessions(paths.data_root)
    args.output_dir = paths.output_dir
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reports = []
    metric_paths = []
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
            result = fit_sta_baseline(aligned, lag_count=lag_count, response_transform=args.response_transform)
            np.savez_compressed(
                session_output / "baseline_kernels.npz",
                full_sta=result.sta,
                rank_one_sta=result.rank_one_sta,
                roi_labels=np.asarray(aligned.roi_labels),
            )
        elif args.model == "ridge":
            print(f"Fitting binned ridge STRF for {len(aligned.roi_labels)} ROIs...", flush=True)
            result = fit_binned_ridge(aligned, response_transform=args.response_transform)
            np.savez_compressed(
                session_output / "ridge_coefficients.npz",
                coefficients=result.coefficients,
                roi_labels=np.asarray(aligned.roi_labels),
            )
        else:
            print(f"Fitting train-selected pixel temporal filter for {len(aligned.roi_labels)} ROIs...", flush=True)
            result = fit_pixel_model(aligned, lag_count=lag_count)
            np.savez_compressed(
                session_output / "pixel_model.npz",
                coefficients=result.coefficients,
                intercepts=result.intercepts,
                selected_pixels=result.selected_pixels,
                test_actual=result.test_actual,
                test_predicted=result.test_predicted,
                test_time_us=result.test_time_us,
                roi_labels=np.asarray(aligned.roi_labels),
                fly=np.asarray(session.fly),
                run_id=np.asarray(session.run_id),
                lag_count=np.asarray(lag_count),
                test_start_eligible_frame=np.asarray(result.report["eligible_frames"] - result.report["test_frames"]),
                stimulus_sha256=np.asarray(aligned.qc["source_sha256"]["stim_realized.npz"]),
                source_sha256_json=np.asarray(json.dumps(aligned.qc["source_sha256"], sort_keys=True)),
            )
        reports.append(result.report)
        metric_paths.append(session_output / ("pixel_metrics.json" if args.model == "pixel" else "baseline_metrics.json"))
    if args.model == "pixel" and not args.qc_only:
        adjust_pixel_reports(reports)
    if not args.qc_only:
        for report, path in zip(reports, metric_paths, strict=True):
            with path.open("w") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False, allow_nan=False)
        reports = [{key: value for key, value in report.items() if key != "roi_metrics"} for report in reports]
    with (args.output_dir / "summary.json").open("w") as handle:
        json.dump(reports, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps(reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
