"""Construct a causal temporal-bin STRF design on the frozen stimulus clock.

Input: digital stimulus [update,225] in -1/+1. Output: one row per eligible
15 Hz update, [update, bins*225]. Each bin averages preceding updates only.
The same feature row may serve many fly/ROI observations without copying it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..ridge import binned_design


@dataclass(frozen=True)
class FeatureDefinition:
    bins: int = 4
    updates_per_bin: int = 10

    @property
    def history_updates(self) -> int:
        return self.bins * self.updates_per_bin

    @property
    def feature_count(self) -> int:
        return self.bins * 225


def build_shared_feature_table(stimulus: np.ndarray, definition: FeatureDefinition) -> np.ndarray:
    """Rows correspond to updates history-1 ... final update, inclusive."""
    if stimulus.ndim != 2 or stimulus.shape[1] != 225 or definition.history_updates < 1:
        raise ValueError("Expected [update,225] stimulus and positive temporal history")
    eligible_update = np.arange(definition.history_updates - 1, len(stimulus), dtype=np.int32)
    return binned_design(stimulus, eligible_update, definition.bins, definition.updates_per_bin)
