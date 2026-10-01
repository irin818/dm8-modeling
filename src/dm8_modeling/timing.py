"""Recorded TTL clocks; Zeiss frame-out is an exposure-time proxy."""

import csv
from pathlib import Path
import numpy as np


def read_clock(path: Path, column: str, *, integer: bool = True) -> np.ndarray:
    """Read one strictly increasing CSV clock [sample], in us or playback s."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    if column not in header:
        raise ValueError(f"Missing {column}: {path}")
    values = np.loadtxt(path, delimiter=",", skiprows=1, usecols=header.index(column),
                        dtype=np.int64 if integer else float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all() or np.any(np.diff(values) <= 0):
        raise ValueError(f"Clock must be finite and strictly increasing: {path}")
    return values


def associate_frames(update_us: np.ndarray, frame_us: np.ndarray, end_us: int) -> tuple[np.ndarray, np.ndarray]:
    """Return last displayed update and payload mask [frame]; no future update."""
    if (update_us.ndim != 1 or frame_us.ndim != 1 or not len(update_us)
            or np.any(np.diff(update_us) <= 0) or np.any(np.diff(frame_us) <= 0)
            or end_us <= update_us[-1]):
        raise ValueError("Invalid stimulus/frame clocks or payload boundary")
    updates = np.searchsorted(update_us, frame_us, side="right") - 1
    return updates, (updates >= 0) & (frame_us < end_us)
