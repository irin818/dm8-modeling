"""Train-selected single-pixel temporal encoding model with blocked validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import AlignedSession
from .model import _finite_or_none, _scores, lagged_design


@dataclass
class PixelResult:
    report: dict
    coefficients: np.ndarray  # ROI x lag, raw-intensity units per stimulus unit
    selected_pixels: np.ndarray  # ROI, flattened row-major stimulus pixel
    test_actual: np.ndarray
    test_predicted: np.ndarray
    test_time_us: np.ndarray


def _fit(x: np.ndarray, y: np.ndarray, penalty: float) -> tuple[np.ndarray, float]:
    """Center using fitting rows only; penalize slopes but not the intercept."""
    xm = x.mean(axis=0, dtype=np.float64)
    ym = float(y.mean())
    xc = x.astype(np.float64) - xm
    yc = y.astype(np.float64) - ym
    beta = np.linalg.solve(xc.T @ xc + penalty * len(x) * np.eye(x.shape[1]), xc.T @ yc)
    return beta, ym - float(xm @ beta)


def _shift_p_values(actual: np.ndarray, predicted: np.ndarray, exclusion: int) -> np.ndarray:
    """Exact two-sided circular-shift null for fixed test predictions."""
    n = len(actual)
    if n <= 2 * exclusion + 1:
        raise ValueError("Test block too short for circular-shift null")
    a = actual.astype(np.float64) - actual.mean(axis=0)
    p = predicted.astype(np.float64) - predicted.mean(axis=0)
    fa = np.fft.rfft(a, axis=0)
    fp = np.fft.rfft(p, axis=0)
    dot = np.fft.irfft(np.conj(fa) * fp, n=n, axis=0)
    denom = np.sqrt(np.sum(a * a, axis=0) * np.sum(p * p, axis=0))
    correlation = np.divide(dot, denom, out=np.full_like(dot, np.nan), where=denom > 0)
    null = np.abs(correlation[exclusion:n - exclusion])
    return (1 + np.sum(null >= np.abs(correlation[0]), axis=0)) / (1 + len(null))


def _bh_q_values(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjustment over all ROIs from all runs."""
    order = np.argsort(p)
    ranks = np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate((p[order] * len(p) / ranks)[::-1])[::-1]
    out = np.empty_like(adjusted)
    out[order] = np.minimum(adjusted, 1)
    return out


def adjust_pixel_reports(reports: list[dict]) -> None:
    """Add one family-wide FDR value after every run has been fitted."""
    entries = [entry for report in reports for entry in report["roi_metrics"]]
    q = _bh_q_values(np.asarray([entry["shift_null_p_two_sided"] for entry in entries]))
    for entry, value in zip(entries, q, strict=True):
        entry["shift_null_q_all_rois"] = float(value)


def fit_pixel_model(
    aligned: AlignedSession,
    lag_count: int = 18,
    penalties: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0, 10.0),
) -> PixelResult:
    """Select location on early 50%, tune on 50-70%, score after a purge.

    The procedure operates on raw ROI mean intensity. It does not establish
    calcium processing, Dm8 identity, physical wavelength or exposure timing.
    """
    if lag_count < 1 or not penalties or any(value <= 0 for value in penalties):
        raise ValueError("Expected positive lag count and positive ridge penalties")
    eligible = aligned.update_index >= lag_count - 1
    update_index = aligned.update_index[eligible]
    y = aligned.response[eligible]
    times = aligned.imaging_time_us[eligible]
    n = len(y)
    train_end = int(n * 0.5)
    validation_start = train_end + lag_count
    validation_end = int(n * 0.7)
    test_start = validation_end + lag_count
    if train_end < 100 or validation_end - validation_start < 100 or n - test_start < 100:
        raise ValueError("Insufficient time-separated training, validation or test rows")

    n_pixels = aligned.stimulus.shape[1]
    design = lagged_design(aligned.stimulus, update_index, lag_count)
    train_y = y[:train_end].astype(np.float64)
    train_x = design[:train_end].astype(np.float64)
    yc = train_y - train_y.mean(axis=0)
    xc = train_x - train_x.mean(axis=0)
    sta = (xc.T @ yc).reshape(lag_count, n_pixels, -1) / train_end
    selected = np.argmax(np.sum(sta * sta, axis=0), axis=0)
    validation_x = design[validation_start:validation_end].astype(np.float64)
    validation_y = y[validation_start:validation_end].astype(np.float64)
    validation_sta = (
        (validation_x - validation_x.mean(axis=0)).T
        @ (validation_y - validation_y.mean(axis=0))
    ).reshape(lag_count, n_pixels, -1) / len(validation_y)
    validation_selected = np.argmax(np.sum(validation_sta * validation_sta, axis=0), axis=0)
    n_rois = y.shape[1]
    coefficients = np.empty((n_rois, lag_count))
    prediction = np.empty((n - test_start, n_rois))
    validation_r2 = np.empty(n_rois)
    selected_penalty = np.empty(n_rois)
    fit_indices = np.r_[0:train_end, validation_start:validation_end]
    for roi in range(n_rois):
        columns = np.arange(lag_count) * n_pixels + selected[roi]
        x = design[:, columns]
        trial = []
        for penalty in penalties:
            beta, intercept = _fit(x[:train_end], y[:train_end, roi], penalty)
            candidate = x[validation_start:validation_end] @ beta + intercept
            score = _scores(y[validation_start:validation_end, roi, None], candidate[:, None])[1][0]
            trial.append(score)
        best = int(np.argmax(trial))
        selected_penalty[roi] = penalties[best]
        validation_r2[roi] = trial[best]
        beta, intercept = _fit(x[fit_indices], y[fit_indices, roi], penalties[best])
        coefficients[roi] = beta
        prediction[:, roi] = x[test_start:] @ beta + intercept

    actual = y[test_start:]
    test_r, test_r2 = _scores(actual, prediction)
    baseline = np.broadcast_to(y[fit_indices].mean(axis=0), actual.shape)
    _, baseline_r2 = _scores(actual, baseline)
    exclusion = max(lag_count, 30)
    shift_p = _shift_p_values(actual, prediction, exclusion)
    roi_metrics = []
    for roi, label in enumerate(aligned.roi_labels):
        px = int(selected[roi])
        roi_metrics.append({
            "roi": label,
            "pixel_row_zero_based": px // 15,
            "pixel_col_zero_based": px % 15,
            "validation_best_pixel_row_zero_based": int(validation_selected[roi]) // 15,
            "validation_best_pixel_col_zero_based": int(validation_selected[roi]) % 15,
            "pixel_stable_train_validation": bool(selected[roi] == validation_selected[roi]),
            "validation_r2": _finite_or_none(validation_r2[roi]),
            "selected_penalty": float(selected_penalty[roi]),
            "test_r": _finite_or_none(test_r[roi]),
            "test_r2": _finite_or_none(test_r2[roi]),
            "constant_baseline_test_r2": _finite_or_none(baseline_r2[roi]),
            "shift_null_p_two_sided": _finite_or_none(shift_p[roi]),
        })
    report = {
        "fly": aligned.session.fly,
        "run_id": aligned.session.run_id,
        "method": "train_selected_single_pixel_ridge_temporal_filter",
        "response_kind": "unprocessed_ROI_mean_intensity",
        "stimulus_kind": "frozen_binary_updates_minus1_plus1",
        "lag_count": lag_count,
        "history_seconds_nominal": lag_count / 15.0,
        "penalties": list(penalties),
        "eligible_frames": n,
        "train_frames": train_end,
        "validation_frames": validation_end - validation_start,
        "test_frames": n - test_start,
        "purge_frames_each": lag_count,
        "train_time_us": [int(times[0]), int(times[train_end - 1])],
        "validation_time_us": [int(times[validation_start]), int(times[validation_end - 1])],
        "test_time_us": [int(times[test_start]), int(times[-1])],
        "pixel_selection": "maximum squared centered training STA across lags",
        "penalty_selection": "maximum validation R2 per ROI",
        "final_fit": "training plus validation rows, excluding first purge",
        "shift_null": f"exact circular shifts of fixed test prediction, excluding ±{exclusion} imaging frames",
        "roi_count": n_rois,
        "median_test_r": _finite_or_none(np.nanmedian(test_r)),
        "median_test_r2": _finite_or_none(np.nanmedian(test_r2)),
        "roi_metrics": roi_metrics,
        "interpretation_limit": "Raw ROI intensity only; no verified Dm8 identity or calcium response. The model family was developed after earlier late-block exploratory results had been inspected.",
    }
    return PixelResult(report, coefficients, selected, actual, prediction, times[test_start:])
