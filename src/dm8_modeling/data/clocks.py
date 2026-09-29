"""Read display/imaging clocks and assign each imaging frame to past stimulus.

DLP and Zeiss TTL values are acquisition-device microseconds; PsychoPy flip
values are playback-clock seconds. Frame-out remains an exposure proxy.
"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np

def _read_clock(path: Path, column: str) -> np.ndarray:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    if column not in header:
        raise ValueError(f"{path} lacks required column {column}")
    values = np.loadtxt(path, delimiter=",", skiprows=1, usecols=header.index(column), dtype=np.int64)
    if values.ndim != 1 or len(values) < 2 or np.any(np.diff(values) <= 0):
        raise ValueError(f"Non-increasing or empty clock: {path}")
    return values


def _read_playback_time(path: Path) -> np.ndarray:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    if "flip_time_s" not in header:
        raise ValueError(f"Missing flip_time_s in {path}")
    values = np.loadtxt(path, delimiter=",", skiprows=1, usecols=header.index("flip_time_s"))
    if np.any(np.diff(values) <= 0):
        raise ValueError(f"Non-increasing flip times in {path}")
    return values


def associate_imaging_with_updates(
    update_times_us: np.ndarray, imaging_times_us: np.ndarray, payload_end_us: int
) -> tuple[np.ndarray, np.ndarray]:
    """Map Zeiss frame-out proxies to last preceding displayed update.

    The start is inclusive and the planned payload end (indexed on recorded
    DLP TTL) is exclusive. The imager's true exposure instant is unknown.
    """
    if (update_times_us.ndim != 1 or imaging_times_us.ndim != 1 or
        len(update_times_us) == 0 or np.any(np.diff(update_times_us) <= 0) or
        np.any(np.diff(imaging_times_us) <= 0) or payload_end_us <= update_times_us[-1]):
        raise ValueError("Invalid aligned update/imaging clocks or payload end")
    index = np.searchsorted(update_times_us, imaging_times_us, side="right") - 1
    included = (index >= 0) & (imaging_times_us < payload_end_us)
    return index, included
