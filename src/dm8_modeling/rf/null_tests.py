"""Circular-shift controls and family-wise BH adjustment for ROI reports."""
from __future__ import annotations
import numpy as np

def _shift_p_values(actual: np.ndarray, predicted: np.ndarray, exclusion: int) -> np.ndarray:
    """Exact two-sided circular-shift null for fixed test predictions."""
    n = len(actual)
    if n <= 2 * exclusion + 1:
        raise ValueError("Test block too short for circular-shift null")
    a = actual.astype(np.float64) - actual.mean(axis=0)
    p = predicted.astype(np.float64) - predicted.mean(axis=0)
    fa = np.fft.rfft(a, axis=0)
    fp = np.fft.rfft(p, axis=0)
    dot = np.fft.irfft(np.conj(fa) * fp, n=n, axis=0)
    denom = np.sqrt(np.sum(a * a, axis=0) * np.sum(p * p, axis=0))
    correlation = np.divide(dot, denom, out=np.full_like(dot, np.nan), where=denom > 0)
    null = np.abs(correlation[exclusion:n - exclusion])
    return (1 + np.sum(null >= np.abs(correlation[0]), axis=0)) / (1 + len(null))


def _bh_q_values(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjustment over all ROIs from all runs."""
    order = np.argsort(p)
    ranks = np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate((p[order] * len(p) / ranks)[::-1])[::-1]
    out = np.empty_like(adjusted)
    out[order] = np.minimum(adjusted, 1)
    return out


def adjust_pixel_reports(reports: list[dict]) -> None:
    """Add one family-wide FDR value after every run has been fitted."""
    entries = [entry for report in reports for entry in report["roi_metrics"]]
    q = _bh_q_values(np.asarray([entry["shift_null_p_two_sided"] for entry in entries]))
    for entry, value in zip(entries, q, strict=True):
        entry["shift_null_q_all_rois"] = float(value)
