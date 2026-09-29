"""Explicit bridge from recorded frames to a model-ready causal design.

`align_session` reads frozen stimulus [9000,225], ROI mean intensity
[payload imaging frame,ROI], marker-locked DLP/Zeiss clocks [microseconds].
This module forms X [eligible imaging frame, lag × 225] and y [eligible
imaging frame, ROI]. X uses only the current and preceding 15 Hz updates.
The response source is not verified ΔF/F; candidate transforms are labelled.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..data import AlignedSession
from ..features.lagged import lagged_design
from ..preprocessing import candidate_response
from .legacy_splits import TemporalSplit, blocked_split


@dataclass(frozen=True)
class ModelDataset:
    X: np.ndarray
    y: np.ndarray
    imaging_time_us: np.ndarray
    update_index: np.ndarray
    roi_labels: tuple[str, ...]
    response_kind: str
    lag_count: int
    split: TemporalSplit


def build_model_dataset(aligned: AlignedSession, lag_count: int = 18,
                        response_kind: str = "raw", validation: bool = True) -> ModelDataset:
    """Create a traceable X/y pair; retained legacy models preserve old numerics."""
    if lag_count < 1:
        raise ValueError("lag_count must be positive")
    eligible = aligned.update_index >= lag_count - 1
    index = aligned.update_index[eligible]
    response = candidate_response(aligned.response, aligned.imaging_time_us, response_kind)[eligible]
    design = lagged_design(aligned.stimulus, index, lag_count)
    split = blocked_split(index, lag_count, validation)
    if len(design) != len(response):
        raise ValueError("X/y row mismatch")
    return ModelDataset(design, response, aligned.imaging_time_us[eligible], index,
                        tuple(aligned.roi_labels), response_kind, lag_count, split)
