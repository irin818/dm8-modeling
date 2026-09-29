"""Low-dimensional, regularized STRF comparison for the recorded white noise."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import AlignedSession
from .model import _finite_or_none, _scores, causal_ema_residual
from .splits import blocked_split


@dataclass
class RidgeResult:
    report: dict
    coefficients: np.ndarray  # temporal bin x 15 x 15 x ROI


def binned_design(
    stimulus: np.ndarray, update_index: np.ndarray, bins: int = 4, updates_per_bin: int = 10
) -> np.ndarray:
    """Average disjoint past-update blocks to reduce STRF parameter count."""
    history = bins * updates_per_bin
    if bins < 1 or updates_per_bin < 1 or stimulus.ndim != 2 or update_index.ndim != 1:
        raise ValueError("Invalid binned-design inputs")
    if len(update_index) == 0 or np.min(update_index) < history - 1 or np.max(update_index) >= len(stimulus):
        raise ValueError("Update indices do not have complete causal history")
    out = np.empty((len(update_index), bins * stimulus.shape[1]), dtype=np.float32)
    for temporal_bin in range(bins):
        lags = np.arange(
            temporal_bin * updates_per_bin,
            (temporal_bin + 1) * updates_per_bin,
        )
        block = stimulus[update_index[:, None] - lags[None, :]]
        out[:, temporal_bin * stimulus.shape[1] : (temporal_bin + 1) * stimulus.shape[1]] = block.mean(axis=1)
    return out


def _ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean_x = x.mean(axis=0, dtype=np.float64)
    mean_y = y.mean(axis=0, dtype=np.float64)
    centered_x = x.astype(np.float64) - mean_x
    centered_y = y.astype(np.float64) - mean_y
    gram = (centered_x.T @ centered_x) / len(x)
    cross = (centered_x.T @ centered_y) / len(x)
    coefficient = np.linalg.solve(gram + alpha * np.eye(gram.shape[0]), cross)
    return coefficient, mean_x, mean_y


def _predict(x: np.ndarray, fit: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    coefficient, mean_x, mean_y = fit
    return (x.astype(np.float64) - mean_x) @ coefficient + mean_y


def fit_binned_ridge(
    aligned: AlignedSession,
    response_transform: str = "raw",
    bins: int = 4,
    updates_per_bin: int = 10,
) -> RidgeResult:
    """Select one ridge penalty on an earlier validation block, then score late test data."""
    history = bins * updates_per_bin
    eligible = aligned.update_index >= history - 1
    index = aligned.update_index[eligible]
    if response_transform == "raw":
        response = aligned.response[eligible]
        response_kind = "unprocessed_ROI_mean_intensity"
    elif response_transform == "causal_ema_60s":
        response = causal_ema_residual(aligned.response, aligned.imaging_time_us)[eligible]
        response_kind = "causal_60s_EMA_residual_of_ROI_mean_intensity"
    else:
        raise ValueError(f"Unknown response transform: {response_transform}")
    if len(response) < 500:
        raise ValueError("Too few usable imaging frames")
    x = binned_design(aligned.stimulus, index, bins, updates_per_bin)
    n = len(response)
    split = blocked_split(index, history, validation=True)
    train_end = split.train.stop
    val_start, val_end = split.validation.start, split.validation.stop
    test_start = split.test.start
    alpha_candidates = (0.001, 0.01, 0.1, 1.0, 10.0)
    validation = []
    for alpha in alpha_candidates:
        fit = _ridge_fit(x[:train_end], response[:train_end], alpha)
        predicted = _predict(x[val_start:val_end], fit)
        r, r2 = _scores(response[val_start:val_end], predicted)
        validation.append({
            "alpha": alpha,
            "median_r": _finite_or_none(np.nanmedian(r)),
            "median_r2": _finite_or_none(np.nanmedian(r2)),
        })
    best = max(validation, key=lambda row: row["median_r2"] if row["median_r2"] is not None else -np.inf)

    # Keep the train/validation purge out of refitting. The test block remains untouched.
    refit_index = np.concatenate((np.arange(train_end), np.arange(val_start, val_end)))
    final_fit = _ridge_fit(x[refit_index], response[refit_index], best["alpha"])
    predicted_test = _predict(x[test_start:], final_fit)
    test_r, test_r2 = _scores(response[test_start:], predicted_test)
    metrics = [
        {"roi": label, "test_r": _finite_or_none(test_r[i]), "test_r2": _finite_or_none(test_r2[i])}
        for i, label in enumerate(aligned.roi_labels)
    ]
    report = {
        "fly": aligned.session.fly,
        "run_id": aligned.session.run_id,
        "method": "temporal_bin_averaged_ridge_STRF",
        "response_kind": response_kind,
        "stimulus_kind": "frozen_binary_updates_minus1_plus1",
        "bins": bins,
        "updates_per_bin": updates_per_bin,
        "history_seconds_nominal": history / 15.0,
        "eligible_frames": n,
        "train_frames": train_end,
        "validation_frames": val_end - val_start,
        "test_frames": n - test_start,
        "purge_frames_at_each_boundary": history,
        "chosen_alpha": best["alpha"],
        "validation_candidates": validation,
        "median_test_r": _finite_or_none(np.nanmedian(test_r)),
        "median_test_r2": _finite_or_none(np.nanmedian(test_r2)),
        "roi_positive_test_r2": int(np.sum(test_r2 > 0)),
        "roi_metrics": metrics,
        "interpretation_limit": "Exploratory binned STRF on unverified ROI signals; same frozen stimulus across flies.",
    }
    return RidgeResult(report, final_fit[0].reshape(bins, 15, 15, -1).astype(np.float32))
