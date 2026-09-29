"""Temporal evaluation blocks with an explicit stimulus-history leak check.

Rows are imaging frames, but each design row consumes multiple 15 Hz updates.
The purge is therefore checked using update indices, not an assumed equality
between the DLP and Zeiss sampling rates. Blocks are chronological within one
fly and never imply independent stimuli across the five flies.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TemporalSplit:
    train: slice
    validation: slice | None
    test: slice
    purge_train_validation: slice | None
    purge_validation_test: slice


def _separate(left_last: int, right_first: int, update_index: np.ndarray, history: int) -> None:
    if right_first <= left_last or update_index[right_first] - history + 1 <= update_index[left_last]:
        raise ValueError("Stimulus histories overlap across evaluation blocks")


def blocked_split(update_index: np.ndarray, history: int, validation: bool) -> TemporalSplit:
    """Reproduce the existing 70/30 or 50/20/30 boundaries and verify histories."""
    if update_index.ndim != 1 or len(update_index) < 500 or history < 1:
        raise ValueError("Expected sorted eligible update indices and positive history")
    if np.any(np.diff(update_index) < 0):
        raise ValueError("Update indices must be nondecreasing")
    n = len(update_index)
    if validation:
        train_end = int(n * .5)
        val_start = train_end + history
        val_end = int(n * .7)
        test_start = val_end + history
        if val_start >= val_end or test_start >= n - 100:
            raise ValueError("Insufficient separated validation or test frames")
        _separate(train_end - 1, val_start, update_index, history)
        _separate(val_end - 1, test_start, update_index, history)
        return TemporalSplit(slice(0, train_end), slice(val_start, val_end), slice(test_start, n),
                             slice(train_end, val_start), slice(val_end, test_start))
    train_end = int(n * .7)
    test_start = train_end + history
    if test_start >= n - 100:
        raise ValueError("Insufficient separated test frames")
    _separate(train_end - 1, test_start, update_index, history)
    return TemporalSplit(slice(0, train_end), None, slice(test_start, n), None,
                         slice(train_end, test_start))
