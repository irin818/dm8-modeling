"""Keep each fly/run as its own model-ready response matrix.

Input is one AlignedSession per fly: stimulus [9000,225], raw ROI intensity
[payload imaging frame,ROI], Zeiss proxy microseconds. Each IndividualDataset
keeps frame/ROI identities and points to a shared causal feature table; X is
[eligible imaging frame, bins*225] when requested. No source file is changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..data import AlignedSession, align_session, discover_sessions
from ..features import FeatureDefinition, build_shared_feature_table
from .splits import GlobalStimulusSplit


@dataclass(frozen=True)
class IndividualDataset:
    aligned: AlignedSession
    feature_table: np.ndarray  # [eligible stimulus update, feature]
    feature_definition: FeatureDefinition
    update_index: np.ndarray  # [imaging frame]
    y_raw: np.ndarray  # [imaging frame, ROI], Results.csv intensity units
    imaging_time_us: np.ndarray  # Zeiss frame-out proxy
    original_sample_index: np.ndarray  # zero-based Results.csv data row
    split_label: np.ndarray  # TRAIN/VALIDATION/TEST/PURGE per frame

    @property
    def fly_id(self) -> str:
        return self.aligned.session.fly

    @property
    def run_id(self) -> str:
        return self.aligned.session.run_id

    @property
    def roi_labels(self) -> tuple[str, ...]:
        return tuple(self.aligned.roi_labels)

    @property
    def X(self) -> np.ndarray:
        return self.features()

    def features(self, rows: np.ndarray | slice | None = None) -> np.ndarray:
        """Materialize only the requested imaging frames, never ROI duplicates."""
        index = self.update_index if rows is None else self.update_index[rows]
        return self.feature_table[index - (self.feature_definition.history_updates - 1)]


def load_individual_datasets(
    data_root: Path, feature_definition: FeatureDefinition, split: GlobalStimulusSplit
) -> list[IndividualDataset]:
    """Build five separate datasets and verify the digital stimulus is shared."""
    aligned = [align_session(session) for session in discover_sessions(data_root)]
    if not aligned:
        raise ValueError("No Dm8 experiment sessions")
    reference = aligned[0].stimulus
    if any(not np.array_equal(reference, item.stimulus) for item in aligned[1:]):
        raise ValueError("Stimulus differs across flies; shared feature table would be invalid")
    if split.history_updates != feature_definition.history_updates:
        raise ValueError("Feature history and global split history must match")
    feature_table = build_shared_feature_table(reference, feature_definition)
    datasets = []
    for item in aligned:
        eligible = item.update_index >= feature_definition.history_updates - 1
        original = item.original_sample_index
        if original is None:
            raise ValueError(f"Missing original Results.csv row indices for {item.session.path}")
        index = item.update_index[eligible]
        datasets.append(IndividualDataset(
            item, feature_table, feature_definition, index, item.response[eligible],
            item.imaging_time_us[eligible], original[eligible], split.labels(index, len(reference)),
        ))
    return datasets
