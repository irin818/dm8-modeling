"""Read Results.csv as raw ROI mean intensity [imaging frame,ROI].

This parser does not infer calcium concentration, F0, or ROI identity.
"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np

def _read_results(path: Path) -> tuple[np.ndarray, list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    labels = header[1:]
    if not labels or len(labels) != len(set(labels)):
        raise ValueError(f"Missing or duplicate ROI columns: {path}")
    values = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != len(labels) + 1:
        raise ValueError(f"Unexpected Results.csv shape: {path}")
    expected_frame = np.arange(1, len(values) + 1)
    if not np.array_equal(values[:, 0], expected_frame):
        raise ValueError(f"Results.csv first column is not consecutive 1-based imaging frames: {path}")
    response = values[:, 1:]
    if not np.isfinite(response).all():
        raise ValueError(f"Non-finite ROI intensity in {path}")
    return response, labels
