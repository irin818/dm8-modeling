"""Causal white-noise STRF baseline and descriptive space/time separability."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..data import AlignedSession
from ..datasets.legacy_splits import blocked_split
from ..features.lagged import lagged_design
from ..preprocessing.fluorescence import causal_ema_residual
from ..evaluation.legacy_metrics import _scores, _finite_or_none


@dataclass
class BaselineResult:
    report: dict
    sta: np.ndarray  # lag x row x column x ROI
    rank_one_sta: np.ndarray


def estimate_reverse_correlation(design: np.ndarray, response: np.ndarray) -> np.ndarray:
    """Return RF [feature,ROI] from X [frame,feature], y [frame,ROI].

    X is a history of digital stimulus commands; y is the declared response
    representation. Both axes are centered on these rows only. Callers must
    supply TRAIN-only rows when the RF is used for selection.
    """
    if design.ndim != 2 or response.ndim != 2 or len(design) != len(response):
        raise ValueError("Expected aligned [frame,feature] and [frame,ROI] arrays")
    return ((design - design.mean(axis=0)).T @
            (response - response.mean(axis=0))) / len(design)








def _calibrated_prediction(
    train_x: np.ndarray, test_x: np.ndarray, train_y: np.ndarray, kernel: np.ndarray
) -> np.ndarray:
    train_projection = train_x @ kernel
    test_projection = test_x @ kernel
    centered_train_y = train_y - train_y.mean(axis=0)
    denominator = np.sum(train_projection**2, axis=0)
    slope = np.divide(
        np.sum(train_projection * centered_train_y, axis=0), denominator,
        out=np.zeros(train_y.shape[1], dtype=np.float64), where=denominator > 0,
    )
    return train_y.mean(axis=0) + test_projection * slope


def fit_sta_baseline(
    aligned: AlignedSession, lag_count: int = 45, response_transform: str = "raw"
) -> BaselineResult:
    """Fit only on an early time block; score on a later, purged block.

    The response is raw ROI mean intensity or its documented causal residual.
    This is a methodological baseline, not a verified Dm8 calcium model or a
    cross-condition generalization result.
    """
    eligible = aligned.update_index >= lag_count - 1
    update_index = aligned.update_index[eligible]
    if response_transform == "raw":
        transformed_response = aligned.response
        response_kind = "unprocessed_ROI_mean_intensity"
    elif response_transform == "causal_ema_60s":
        transformed_response = causal_ema_residual(aligned.response, aligned.imaging_time_us)
        response_kind = "causal_60s_EMA_residual_of_ROI_mean_intensity"
    else:
        raise ValueError(f"Unknown response transform: {response_transform}")
    response = transformed_response[eligible]
    times = aligned.imaging_time_us[eligible]
    if len(response) < 500:
        raise ValueError(f"Too few imaging frames with complete history: {aligned.session.path}")
    split = blocked_split(update_index, lag_count, validation=False)
    n_train = split.train.stop
    test_start = split.test.start
    gap = split.purge_validation_test.stop - split.purge_validation_test.start

    design = lagged_design(aligned.stimulus, update_index, lag_count)
    train_x = design[:n_train]
    test_x = design[test_start:]
    train_y = response[:n_train]
    test_y = response[test_start:]
    x_mean = train_x.mean(axis=0)
    train_x = train_x - x_mean
    test_x = test_x - x_mean
    y_mean = train_y.mean(axis=0)

    # White-noise reverse correlation; a later stage will compare regularized
    # predictive fits under the same split. Keep this estimator separate.
    kernel = (train_x.T @ (train_y - y_mean)) / n_train
    n_pixels = aligned.stimulus.shape[1]
    n_rois = train_y.shape[1]
    rank_one = np.empty_like(kernel)
    separability = np.empty(n_rois)
    for roi in range(n_rois):
        matrix = kernel[:, roi].reshape(lag_count, n_pixels)
        u, singular, vh = np.linalg.svd(matrix, full_matrices=False)
        rank_one[:, roi] = (singular[0] * np.outer(u[:, 0], vh[0])).reshape(-1)
        separability[roi] = singular[0] ** 2 / np.sum(singular**2) if np.any(singular) else np.nan

    full_prediction = _calibrated_prediction(train_x, test_x, train_y, kernel)
    rank_one_prediction = _calibrated_prediction(train_x, test_x, train_y, rank_one)
    full_r, full_r2 = _scores(test_y, full_prediction)
    rank_one_r, rank_one_r2 = _scores(test_y, rank_one_prediction)
    roi_metrics = []
    for i, label in enumerate(aligned.roi_labels):
        roi_metrics.append({
            "roi": label,
            "full_sta_test_r": _finite_or_none(full_r[i]),
            "full_sta_test_r2": _finite_or_none(full_r2[i]),
            "rank_one_test_r": _finite_or_none(rank_one_r[i]),
            "rank_one_test_r2": _finite_or_none(rank_one_r2[i]),
            "rank_one_kernel_energy_fraction": _finite_or_none(separability[i]),
        })
    finite_r = np.isfinite(full_r)
    report = {
        "fly": aligned.session.fly,
        "run_id": aligned.session.run_id,
        "method": "white_noise_STA_with_train_only_gain_and_intercept",
        "response_kind": response_kind,
        "stimulus_kind": "frozen_binary_updates_minus1_plus1",
        "lag_count": lag_count,
        "history_seconds_nominal": lag_count / 15.0,
        "eligible_frames": len(response),
        "train_frames": n_train,
        "purge_frames": gap,
        "test_frames": len(test_y),
        "train_time_us": [int(times[0]), int(times[n_train - 1])],
        "test_time_us": [int(times[test_start]), int(times[-1])],
        "roi_count": n_rois,
        "median_full_sta_test_r": _finite_or_none(np.nanmedian(full_r)),
        "median_full_sta_test_r2": _finite_or_none(np.nanmedian(full_r2)),
        "median_rank_one_test_r": _finite_or_none(np.nanmedian(rank_one_r)),
        "median_rank_one_test_r2": _finite_or_none(np.nanmedian(rank_one_r2)),
        "median_rank_one_kernel_energy_fraction": _finite_or_none(np.nanmedian(separability)),
        "roi_positive_full_sta_test_r": int(np.sum(full_r[finite_r] > 0)),
        "roi_metrics": roi_metrics,
        "interpretation_limit": (
            "Rank-one kernel energy is descriptive; held-out prediction is needed before "
            "claiming space-time separability. ROI identities and calcium preprocessing are unverified."
        ),
    }
    return BaselineResult(
        report,
        kernel.reshape(lag_count, 15, 15, n_rois).astype(np.float32),
        rank_one.reshape(lag_count, 15, 15, n_rois).astype(np.float32),
    )
