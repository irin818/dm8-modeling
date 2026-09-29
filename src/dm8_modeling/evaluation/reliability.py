"""Select stimulus-responsive ROIs without consulting any test response.

Input: individual causal X [imaging frame,temporal bin*225] and training-only
standardized y [imaging frame,ROI]. The first training half estimates an RF;
the second half supplies split-half and circular-shift evidence. Validation
stability is reported separately, avoiding a test-informed selection rule.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..datasets.splits import TRAIN, VALIDATION
from ..rf.null_tests import _shift_p_values
from ..rf.sta import estimate_reverse_correlation


@dataclass(frozen=True)
class ReliabilityResult:
    fly_id: str
    roi_labels: tuple[str, ...]
    selected: np.ndarray  # [ROI], bool
    split_half_kernel_r: np.ndarray
    train_projection_r: np.ndarray
    train_shift_null_p: np.ndarray
    validation_projection_r: np.ndarray
    validation_pixel_stable: np.ndarray
    train_zero_fraction: np.ndarray
    peak_pixel: np.ndarray
    first_half_kernel: np.ndarray  # [feature,ROI], TRAIN first half
    second_half_kernel: np.ndarray  # [feature,ROI], TRAIN second half
    validation_kernel: np.ndarray  # [feature,ROI], diagnostic only

    def records(self) -> list[dict]:
        return [{"fly_id": self.fly_id, "roi_id": label, "train_defined_responsive": bool(self.selected[i]),
                 "split_half_kernel_r": float(self.split_half_kernel_r[i]),
                 "train_projection_r": float(self.train_projection_r[i]),
                 "train_shift_null_p": float(self.train_shift_null_p[i]),
                 "validation_projection_r": float(self.validation_projection_r[i]),
                 "validation_pixel_stable": bool(self.validation_pixel_stable[i]),
                 "train_zero_fraction": float(self.train_zero_fraction[i]),
                 "peak_pixel_row": int(self.peak_pixel[i] // 15),
                 "peak_pixel_col": int(self.peak_pixel[i] % 15)}
                for i, label in enumerate(self.roi_labels)]


def _column_correlation(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = left - left.mean(axis=0)
    right = right - right.mean(axis=0)
    denominator = np.linalg.norm(left, axis=0) * np.linalg.norm(right, axis=0)
    return np.divide(np.sum(left * right, axis=0), denominator,
                     out=np.zeros(left.shape[1]), where=denominator > 0)


def assess_training_reliability(individual, processed, selection: dict | None = None) -> ReliabilityResult:
    """Estimate TRAIN RF reliability for X [frame,bin*pixel] and y [frame,ROI].

    `selection` contains the thresholds recorded in the experiment config.
    The validation projection is diagnostic only; TEST responses are unused.
    """
    selection = selection or {
        "train_shift_null_p_below": 0.05,
        "split_half_kernel_r_above": 0.0,
        "train_zero_fraction_below": 0.2,
    }
    train = np.flatnonzero(individual.split_label == TRAIN)
    validation = individual.split_label == VALIDATION
    if len(train) < 200 or not np.any(validation):
        raise ValueError("Training halves and validation rows required for ROI selection")
    midpoint = len(train) // 2
    first, second = train[:midpoint], train[midpoint:]
    y = processed.values.astype(np.float64)
    x1 = individual.features(first).astype(np.float64)
    x2 = individual.features(second).astype(np.float64)
    xv = individual.features(validation).astype(np.float64)
    k1 = estimate_reverse_correlation(x1, y[first])
    k2 = estimate_reverse_correlation(x2, y[second])
    kv = estimate_reverse_correlation(xv, y[validation])
    agreement = _column_correlation(k1, k2)
    projection = (x2 - x2.mean(axis=0)) @ k1
    projection_r = _column_correlation(y[second], projection)
    shift_p = _shift_p_values(y[second], projection, exclusion=30)
    bins = individual.feature_definition.bins
    train_peak = np.argmax(np.sum(k1.reshape(bins, 225, -1) ** 2, axis=0), axis=0)
    val_peak = np.argmax(np.sum(kv.reshape(bins, 225, -1) ** 2, axis=0), axis=0)
    pixel_stable = (np.abs(train_peak // 15 - val_peak // 15) <= 1) & (
        np.abs(train_peak % 15 - val_peak % 15) <= 1)
    validation_projection_r = _column_correlation(y[validation],
                                                   (xv - xv.mean(axis=0)) @ k1)
    zeros = np.mean(individual.y_raw[first] == 0, axis=0)
    selected = ((shift_p < float(selection["train_shift_null_p_below"])) &
                (projection_r > 0) &
                (agreement > float(selection["split_half_kernel_r_above"])) &
                (zeros < float(selection["train_zero_fraction_below"])))
    return ReliabilityResult(individual.fly_id, individual.roi_labels, selected, agreement,
                             projection_r, shift_p, validation_projection_r,
                             pixel_stable, zeros, train_peak, k1, k2, kv)
