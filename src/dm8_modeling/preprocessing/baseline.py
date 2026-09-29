"""Estimate past-only EMA F0 [frame,ROI] from intensity and microsecond times."""
from __future__ import annotations
import numpy as np

def causal_ema_baseline(response: np.ndarray, times_us: np.ndarray, tau_seconds: float = 60.0) -> np.ndarray:
    """F0 candidate [frame, ROI], updated from current and earlier samples only."""
    if response.ndim != 2 or times_us.shape != (len(response),) or len(response) < 1:
        raise ValueError("Expected nonempty [frame, ROI] response and matching timestamps")
    if tau_seconds <= 0 or not np.isfinite(response).all() or np.any(np.diff(times_us) <= 0):
        raise ValueError("Expected finite responses, positive tau, increasing timestamps")
    baseline = np.empty_like(response, dtype=np.float64)
    baseline[0] = response[0]
    for frame in range(1, len(response)):
        weight = -np.expm1(-(times_us[frame] - times_us[frame - 1]) / 1e6 / tau_seconds)
        baseline[frame] = baseline[frame - 1] + weight * (response[frame] - baseline[frame - 1])
    return baseline
