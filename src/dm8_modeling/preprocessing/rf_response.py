"""Offline Li-style response for descriptive RF analysis, never forecasting.

The paper describes a Gaussian low-pass baseline with 10 s standard
deviation, followed by subtraction. This implementation uses the median
Zeiss frame interval (the recorded jitter is checked) and reflected edges.
The caller chooses the analysis segment and records how reflected edges are
handled. Phase 6.1 trims each TRAIN half; Phase 6.2 uses the full payload.
"""

from __future__ import annotations

import numpy as np


def li_style_relative_response(
    raw: np.ndarray, times_us: np.ndarray, sigma_seconds: float = 10.0,
    truncate_sigma: float = 3.0,
) -> tuple[np.ndarray, int]:
    """Return ``F - Gaussian_sigma(F)`` and the edge margin in frames.

    The centered Gaussian uses future observations *within the supplied
    segment*. It is NON-CAUSAL / OFFLINE RF CHARACTERIZATION ONLY.
    """
    if raw.ndim != 2 or times_us.shape != (len(raw),) or len(raw) < 3:
        raise ValueError("Expected nonempty [frame,ROI] trace and timestamps")
    if not np.isfinite(raw).all() or sigma_seconds <= 0 or truncate_sigma <= 0:
        raise ValueError("Trace must be finite and smoothing parameters positive")
    intervals = np.diff(times_us.astype(np.float64))
    if np.any(intervals <= 0):
        raise ValueError("Imaging timestamps must increase")
    interval = float(np.median(intervals))
    if np.max(np.abs(intervals - interval)) > 0.05 * interval:
        raise ValueError("Gaussian frame approximation requires near-uniform sampling")
    sigma_frames = sigma_seconds * 1_000_000 / interval
    margin = int(np.ceil(truncate_sigma * sigma_frames))
    if 2 * margin >= len(raw):
        raise ValueError("Trace segment is too short for the Gaussian edge margin")
    offsets = np.arange(-margin, margin + 1, dtype=np.float64)
    kernel = np.exp(-0.5 * (offsets / sigma_frames) ** 2)
    kernel /= kernel.sum()
    padded = np.pad(raw.astype(np.float64), ((margin, margin), (0, 0)), mode="reflect")
    fft_length = len(padded) + len(kernel) - 1
    spectrum = np.fft.rfft(padded, n=fft_length, axis=0)
    baseline = np.fft.irfft(
        spectrum * np.fft.rfft(kernel, n=fft_length)[:, None], n=fft_length, axis=0
    )[2 * margin:2 * margin + len(raw)]
    return (raw.astype(np.float64) - baseline).astype(np.float32), margin
