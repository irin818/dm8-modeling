"""Historical ROI correlation/R2 and finite-JSON conversion; preserves old scores."""
from __future__ import annotations
import numpy as np

def _scores(actual: np.ndarray, predicted: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    actual = actual.astype(np.float64)
    predicted = predicted.astype(np.float64)
    centered_y = actual - actual.mean(axis=0)
    centered_p = predicted - predicted.mean(axis=0)
    denominator = np.sqrt(np.sum(centered_y**2, axis=0) * np.sum(centered_p**2, axis=0))
    correlation = np.divide(
        np.sum(centered_y * centered_p, axis=0), denominator,
        out=np.full(actual.shape[1], np.nan), where=denominator > 0,
    )
    variance = np.sum(centered_y**2, axis=0)
    r2 = np.divide(
        np.sum((actual - predicted) ** 2, axis=0), variance,
        out=np.full(actual.shape[1], np.nan), where=variance > 0,
    )
    return correlation, 1 - r2


def _finite_or_none(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None
