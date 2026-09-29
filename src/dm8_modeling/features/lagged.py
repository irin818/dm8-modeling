"""Form causal current-and-past stimulus histories [sample,lag x pixel]."""
from __future__ import annotations
import numpy as np

def lagged_design(stimulus: np.ndarray, update_index: np.ndarray, lag_count: int) -> np.ndarray:
    """Map digital stimulus [update,pixel] to X [sample,lag*pixel].

    `update_index [sample]` selects the current update for each row; feature
    order is current, then successively older updates. Values remain digital
    −1/+1 commands and carry no measured irradiance unit. Incomplete history
    is rejected, so no future update enters a prediction.
    """
    if lag_count < 1 or stimulus.ndim != 2 or update_index.ndim != 1:
        raise ValueError("Expected 2-D stimulus, 1-D update indices, and positive lag_count")
    if len(update_index) == 0 or np.min(update_index) < lag_count - 1 or np.max(update_index) >= len(stimulus):
        raise ValueError("Update indices do not have complete causal history")
    lag_indices = update_index[:, None] - np.arange(lag_count)[None, :]
    return np.ascontiguousarray(stimulus[lag_indices].reshape(len(update_index), -1), dtype=np.float32)
