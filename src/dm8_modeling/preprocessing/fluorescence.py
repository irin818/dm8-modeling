"""Past-only F0 candidates for raw Results.csv intensity [frame,ROI].

Time is Zeiss proxy microseconds. Outputs remain exploratory, not official
DeltaF/F or verified neural calcium activity.
"""
from __future__ import annotations
import numpy as np

def causal_ema_baseline(response: np.ndarray, times_us: np.ndarray, tau_seconds: float = 60.0) -> np.ndarray:
    """F0 candidate [frame, ROI], updated from current and earlier samples only."""
    if response.ndim != 2 or times_us.shape != (len(response),) or len(response) < 2:
        raise ValueError("Expected nonempty [frame, ROI] response and matching timestamps")
    if tau_seconds <= 0 or not np.isfinite(response).all() or np.any(np.diff(times_us) <= 0):
        raise ValueError("Expected finite responses, positive tau, increasing timestamps")
    baseline = np.empty_like(response, dtype=np.float64)
    baseline[0] = response[0]
    for frame in range(1, len(response)):
        weight = -np.expm1(-(times_us[frame] - times_us[frame - 1]) / 1e6 / tau_seconds)
        baseline[frame] = baseline[frame - 1] + weight * (response[frame] - baseline[frame - 1])
    return baseline


def candidate_response(response: np.ndarray, times_us: np.ndarray, kind: str) -> np.ndarray:
    """Return raw, baseline-subtracted, or candidate ΔF/F in frame × ROI order."""
    if kind == "raw":
        return response.copy()
    if kind == "causal_block_median_residual_60s":
        if response.ndim != 2 or times_us.shape != (len(response),) or np.any(np.diff(times_us) <= 0):
            raise ValueError("Expected aligned response and increasing timestamps")
        residual = np.empty_like(response, dtype=np.float32)
        # Refresh a robust baseline every ~10 s, using only the preceding
        # 60 s. The held baseline is applied to the next block, never fitted
        # from its current or future response values.
        block = max(1, int(round(10_000_000 / np.median(np.diff(times_us)))))
        for start in range(0, len(response), block):
            stop = min(start + block, len(response))
            past_start = int(np.searchsorted(times_us, times_us[start] - 60_000_000))
            baseline = np.median(response[past_start:start], axis=0) if past_start < start else response[start - 1] if start else response[0]
            residual[start:stop] = response[start:stop] - baseline
        return residual
    baseline = causal_ema_baseline(response, times_us)
    residual = response - baseline
    if kind == "causal_ema_residual_60s":
        return residual.astype(np.float32)
    if kind == "candidate_ema_dff_60s":
        # Zero-valued ROIs exist in these records. A fixed one-intensity-unit
        # floor keeps this sensitivity check finite; it is not calibrated F0.
        return (residual / np.maximum(baseline, 1.0)).astype(np.float32)
    raise ValueError(f"Unknown candidate response: {kind}")
