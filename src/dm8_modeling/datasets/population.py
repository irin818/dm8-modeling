"""Per-fly population response averaged over training-defined ROI members.

Input is standardized [imaging frame,ROI] from one fly. Output is one
population response [imaging frame] on that fly's original aligned timeline.
Membership is fixed using training/validation only and is saved explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PopulationDataset:
    fly_id: str
    run_id: str
    response: np.ndarray  # [imaging frame], dimensionless training z-score average
    update_index: np.ndarray
    split_label: np.ndarray
    roi_membership: tuple[str, ...]
    aggregation: str
    selection_rule: str


def build_population_dataset(individual, processed, reliability, aggregation: str = "mean",
                             selected_only: bool = True) -> PopulationDataset:
    if processed.preprocessing_kind != "train_zscore":
        raise ValueError("Population averaging requires training-standardized responses")
    selected = reliability.selected if selected_only else np.ones(len(individual.roi_labels), dtype=bool)
    if not np.any(selected):
        raise ValueError(f"No training-defined responsive ROIs in {individual.fly_id}")
    values = processed.values[:, selected]
    if aggregation == "mean":
        response = values.mean(axis=1)
    elif aggregation == "median":
        response = np.median(values, axis=1)
    else:
        raise ValueError(f"Unknown population aggregation: {aggregation}")
    return PopulationDataset(individual.fly_id, individual.run_id, response.astype(np.float32),
                             individual.update_index, individual.split_label,
                             tuple(np.asarray(individual.roi_labels)[selected]), aggregation,
                             "TRAIN_DEFINED_RESPONSIVE" if selected_only else "ALL_ROIS")
