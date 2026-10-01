"""Offline fluorescence baseline subtraction; never used for forecasting."""

import numpy as np


def relative_response(raw: np.ndarray, times_us: np.ndarray, config: dict) -> tuple[np.ndarray, int]:
    """Return F−Gaussian10s(F) [frame,ROI] and 3-sigma margin; reflect edges."""
    if raw.ndim != 2 or times_us.shape != (len(raw),) or len(raw) < 3 or not np.isfinite(raw).all():
        raise ValueError("Expected finite ROI intensity and matching timestamps")
    intervals = np.diff(times_us.astype(np.float64))
    interval = float(np.median(intervals))
    if np.any(intervals <= 0) or np.max(np.abs(intervals - interval)) > .05 * interval:
        raise ValueError("Gaussian frame approximation requires near-uniform increasing timestamps")
    sigma = config["gaussian_sigma_seconds"] * 1_000_000 / interval
    margin = int(np.ceil(config["gaussian_truncate_sigma"] * sigma))
    if sigma <= 0 or margin < 1 or 2 * margin >= len(raw):
        raise ValueError("Invalid Gaussian kernel or too few frames")
    offsets = np.arange(-margin, margin + 1, dtype=np.float64)
    kernel = np.exp(-.5 * (offsets / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.pad(raw.astype(np.float64), ((margin, margin), (0, 0)), mode="reflect")
    fft_length = len(padded) + len(kernel) - 1
    baseline = np.fft.irfft(np.fft.rfft(padded, n=fft_length, axis=0)
        * np.fft.rfft(kernel, n=fft_length)[:, None], n=fft_length, axis=0)[2*margin:2*margin+len(raw)]
    return (raw.astype(np.float64) - baseline).astype(np.float32), margin
