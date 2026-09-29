"""Global stimulus-update partitions shared by all five biological recordings.

The frozen stimulus is identical across flies. Therefore all flies assign the
same update interval to train, validation, purge or test. A gap of `history-1`
updates makes the actual past-stimulus histories disjoint across blocks.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


TRAIN, VALIDATION, TEST, PURGE, UNUSED = 0, 1, 2, 3, 4
SPLIT_NAMES = ("train", "validation", "test", "purge", "unused")


@dataclass(frozen=True)
class GlobalStimulusSplit:
    name: str
    history_updates: int
    train_end_update: int  # exclusive
    validation_end_update: int  # exclusive
    test_end_update: int  # exclusive

    @property
    def validation_start_update(self) -> int:
        return self.train_end_update + self.history_updates - 1

    @property
    def test_start_update(self) -> int:
        return self.validation_end_update + self.history_updates - 1

    def validate(self, stimulus_update_count: int) -> None:
        if not (self.history_updates > 0 and self.history_updates - 1 < self.train_end_update <=
                self.validation_start_update < self.validation_end_update <= self.test_start_update <
                self.test_end_update <= stimulus_update_count):
            raise ValueError("Invalid global stimulus split or insufficient purge")
        if self.validation_start_update - (self.history_updates - 1) < self.train_end_update:
            raise ValueError("Train and validation stimulus histories overlap")
        if self.test_start_update - (self.history_updates - 1) < self.validation_end_update:
            raise ValueError("Validation and test stimulus histories overlap")

    def labels(self, update_index: np.ndarray, stimulus_update_count: int) -> np.ndarray:
        self.validate(stimulus_update_count)
        if update_index.ndim != 1 or np.any((update_index < 0) | (update_index >= stimulus_update_count)):
            raise ValueError("Invalid per-frame stimulus update index")
        labels = np.full(len(update_index), UNUSED, dtype=np.uint8)
        labels[(update_index >= self.history_updates - 1) & (update_index < self.train_end_update)] = TRAIN
        labels[(update_index >= self.train_end_update) &
               (update_index < self.validation_start_update)] = PURGE
        labels[(update_index >= self.validation_start_update) &
               (update_index < self.validation_end_update)] = VALIDATION
        labels[(update_index >= self.validation_end_update) &
               (update_index < self.test_start_update)] = PURGE
        labels[(update_index >= self.test_start_update) & (update_index < self.test_end_update)] = TEST
        return labels

    def intervals(self) -> dict[str, list[int]]:
        return {"train": [self.history_updates - 1, self.train_end_update],
                "validation": [self.validation_start_update, self.validation_end_update],
                "test": [self.test_start_update, self.test_end_update],
                "purge_train_validation": [self.train_end_update, self.validation_start_update],
                "purge_validation_test": [self.validation_end_update, self.test_start_update]}


SplitDefinition = GlobalStimulusSplit
