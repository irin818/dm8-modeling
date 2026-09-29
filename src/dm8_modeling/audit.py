"""Read-only response, clock and exploratory RF audit for every fly and ROI.

Outputs are derived tables under --output-dir. RF evidence is a within-run
signal quality check, not proof of cell identity or an official ΔF/F pipeline.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from dm8_modeling.data import _read_clock, _read_results, align_session, discover_sessions
from dm8_modeling.model import lagged_design
from dm8_modeling.pixel import _shift_p_values
from dm8_modeling.preprocessing import candidate_response


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No audit rows")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _corr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    denominator = np.sqrt(np.sum(a * a, axis=0) * np.sum(b * b, axis=0))
    return np.divide(np.sum(a * b, axis=0), denominator, out=np.zeros(a.shape[1]), where=denominator > 0)


def _clock_summary(name: str, values: np.ndarray, expected_us: float | None) -> dict:
    intervals = np.diff(values)
    median = float(np.median(intervals))
    return {
        "clock": name, "count": len(values), "start_us": int(values[0]), "end_us": int(values[-1]),
        "duplicate_or_reverse": int(np.sum(intervals <= 0)), "median_interval_us": median,
        "p01_interval_us": float(np.quantile(intervals, .01)),
        "p99_interval_us": float(np.quantile(intervals, .99)),
        "max_interval_us": int(np.max(intervals)),
        "intervals_over_1p5x_median": int(np.sum(intervals > 1.5 * median)),
        "nominal_interval_us": expected_us,
    }


def _response_rows(fly: str, run_id: str, response: np.ndarray, labels: list[str], fs_hz: float) -> list[dict]:
    rows = []
    count = len(response)
    first = response[:count // 10]
    last = response[-count // 10:]
    for idx, label in enumerate(labels):
        signal = response[:, idx].astype(np.float64)
        mean = float(np.mean(signal))
        std = float(np.std(signal))
        median = float(np.median(signal))
        mad = float(np.median(np.abs(signal - median)))
        step = np.diff(signal)
        jump_scale = float(np.median(np.abs(step - np.median(step))))
        frequencies = np.fft.rfftfreq(count, 1 / fs_hz)
        power = np.abs(np.fft.rfft(signal - mean)) ** 2
        power[0] = 0
        peak_hz = float(frequencies[int(np.argmax(power))])
        rows.append({
            "fly": fly, "run_id": run_id, "roi": label, "count": count,
            "mean": mean, "median": median, "std": std, "cv": std / mean if mean else "",
            "min": float(np.min(signal)), "p01": float(np.quantile(signal, .01)),
            "p05": float(np.quantile(signal, .05)), "p95": float(np.quantile(signal, .95)),
            "p99": float(np.quantile(signal, .99)), "max": float(np.max(signal)),
            "zero_count": int(np.sum(signal == 0)),
            "at_max_count": int(np.sum(signal == np.max(signal))),
            "first_last_decile_change_fraction": float((np.mean(last[:, idx]) - np.mean(first[:, idx])) / mean) if mean else "",
            "robust_outlier_count": int(np.sum(np.abs(signal - median) > 6 * 1.4826 * mad)) if mad else 0,
            "abrupt_jump_count": int(np.sum(np.abs(step - np.median(step)) > 8 * 1.4826 * jump_scale)) if jump_scale else 0,
            "lag1_autocorrelation": float(_corr(signal[:-1, None], signal[1:, None])[0]),
            "psd_peak_hz": peak_hz,
        })
    return rows


def _rf_rows(aligned, pixel_metrics: dict | None) -> tuple[list[dict], list[dict]]:
    """Split the early 70% for two independent STA estimates; score the late 30%."""
    lags = 18
    eligible = aligned.update_index >= lags - 1
    indices = aligned.update_index[eligible]
    design = lagged_design(aligned.stimulus, indices, lags).astype(np.float64)
    y_raw = aligned.response[eligible]
    split = int(len(design) * .35)
    early_end = int(len(design) * .7)
    x1, x2, xt = design[:split], design[split:early_end], design[early_end:]
    x1 = x1 - x1.mean(axis=0)
    x2 = x2 - x2.mean(axis=0)
    xt = xt - design[:early_end].mean(axis=0)
    roi_rows = []
    candidate_rows = []
    pixel_by_label = {row["roi"]: row for row in (pixel_metrics or {}).get("roi_metrics", [])}
    for kind in ("raw", "causal_ema_residual_60s", "candidate_ema_dff_60s"):
        y = candidate_response(aligned.response, aligned.imaging_time_us, kind)[eligible].astype(np.float64)
        y1, y2, yt = y[:split], y[split:early_end], y[early_end:]
        k1 = x1.T @ (y1 - y1.mean(axis=0)) / len(x1)
        k2 = x2.T @ (y2 - y2.mean(axis=0)) / len(x2)
        agreement = _corr(k1, k2)
        prediction = xt @ k1
        test_r = _corr(yt, prediction)
        candidate_rows.append({"fly": aligned.session.fly, "run_id": aligned.session.run_id,
                               "candidate": kind, "median_split_half_kernel_r": float(np.median(agreement)),
                               "median_late_projection_r": float(np.median(test_r)),
                               "positive_late_projection_roi_count": int(np.sum(test_r > 0))})
        if kind != "raw":
            continue
        # Circularly shift the second early block's ROI trace against the
        # first-block RF projection. This preserves autocorrelation while
        # breaking the stimulus/response alignment; 30-frame near shifts are
        # excluded. The null is a projection test, not a full RF FDR test.
        split_null_p = _shift_p_values(y2, x2 @ k1, 30)
        for roi, label in enumerate(aligned.roi_labels):
            matrix = k1[:, roi].reshape(lags, 225)
            singular = np.linalg.svd(matrix, compute_uv=False)
            energy = float(singular[0] ** 2 / np.sum(singular ** 2)) if np.any(singular) else 0.0
            pixel = pixel_by_label.get(label, {})
            q = pixel.get("shift_null_q_all_rois")
            pixel_r = pixel.get("test_r")
            stable = bool(pixel.get("pixel_stable_train_validation"))
            if q is not None and q < .05 and pixel_r is not None and pixel_r > 0 and stable and agreement[roi] > 0 and split_null_p[roi] < .05:
                confidence = "HIGH_CONFIDENCE_RESPONSIVE"
            elif q is not None and q < .05 and pixel_r is not None and pixel_r > 0:
                confidence = "MODERATE_CONFIDENCE"
            elif agreement[roi] > 0 and test_r[roi] > 0:
                confidence = "LOW_CONFIDENCE"
            else:
                confidence = "NO_DETECTABLE_RF"
            center = int(np.argmax(np.sum(matrix * matrix, axis=0)))
            roi_rows.append({"fly": aligned.session.fly, "run_id": aligned.session.run_id,
                             "roi": label, "split_half_kernel_r": float(agreement[roi]),
                             "split_half_projection_shift_null_p": float(split_null_p[roi]),
                             "late_projection_r": float(test_r[roi]), "rank_one_energy_fraction": energy,
                             "train_rf_peak_row": center // 15, "train_rf_peak_col": center % 15,
                             "pixel_model_test_r": pixel_r, "pixel_model_shift_q": q,
                             "pixel_location_stable": stable, "rf_confidence": confidence})
    return roi_rows, candidate_rows


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


if __name__ == "__main__":
    main()
