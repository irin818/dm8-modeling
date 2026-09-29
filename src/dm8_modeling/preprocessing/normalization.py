"""Fit per-ROI response scale strictly on the global training interval.

Input is a session [eligible imaging frame,ROI] in raw Results.csv intensity
or an explicitly named causal candidate. Validation/test use the fixed train
mean and standard deviation. Zero-variance ROIs use scale 1 and are flagged.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..datasets.splits import TRAIN
from .fluorescence import candidate_response


@dataclass(frozen=True)
class ResponseScaler:
    mean: np.ndarray  # [ROI], training-only
    scale: np.ndarray  # [ROI], training-only
    normalization: str
    zero_variance_roi: np.ndarray  # [ROI]

    def transform(self, values: np.ndarray) -> np.ndarray:
        if values.ndim != 2 or values.shape[1] != len(self.mean):
            raise ValueError("Response/scaler ROI mismatch")
        return ((values - self.mean) / self.scale).astype(np.float32)

    def inverse(self, values: np.ndarray) -> np.ndarray:
        return values * self.scale + self.mean


@dataclass(frozen=True)
class ProcessedResponse:
    values: np.ndarray  # [eligible imaging frame,ROI]
    response_kind: str
    preprocessing_kind: str
    scaler: ResponseScaler
    train_frame_count: int


def fit_response_scaler(values: np.ndarray, train_mask: np.ndarray, normalization: str) -> ResponseScaler:
    if values.ndim != 2 or train_mask.shape != (len(values),) or not np.any(train_mask):
        raise ValueError("Training response rows are required")
    if normalization == "raw":
        return ResponseScaler(np.zeros(values.shape[1]), np.ones(values.shape[1]), normalization,
                              np.zeros(values.shape[1], dtype=bool))
    if normalization != "train_zscore":
        raise ValueError(f"Unknown response normalization: {normalization}")
    train = values[train_mask].astype(np.float64)
    mean = train.mean(axis=0)
    std = train.std(axis=0)
    zero_variance = std < 1e-8
    return ResponseScaler(mean, np.where(zero_variance, 1.0, std), normalization, zero_variance)


def process_individual_response(individual, response_kind: str, normalization: str) -> ProcessedResponse:
    """Compute past-only target candidate, then freeze scale from TRAIN only."""
    if response_kind == "raw":
        values = individual.y_raw
    else:
        full = candidate_response(individual.aligned.response, individual.aligned.imaging_time_us, response_kind)
        eligible = individual.aligned.update_index >= individual.feature_definition.history_updates - 1
        values = full[eligible]
    if values.shape != individual.y_raw.shape or not np.isfinite(values).all():
        raise ValueError("Candidate response is misaligned or nonfinite")
    train_mask = individual.split_label == TRAIN
    scaler = fit_response_scaler(values, train_mask, normalization)
    return ProcessedResponse(scaler.transform(values), response_kind, normalization, scaler, int(train_mask.sum()))
