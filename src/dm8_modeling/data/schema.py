"""Experiment objects: session identity and time-aligned raw stimulus/ROI response.

Stimulus is [update,225] in digital ±1; response is [imaging frame,ROI]
in Results.csv intensity units. Timestamps use the Due microsecond clock.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass(frozen=True)
class Session:
    path: Path
    fly: str
    run_id: str


@dataclass(frozen=True)
class SessionPaths:
    """Paths to immutable source records for one fly/run."""

    root: Path

    @property
    def stimulus_package(self) -> Path:
        return self.root / "stimulus_package"

    @property
    def results_csv(self) -> Path:
        return self.root / "Results.csv"

    @property
    def locked_dlp_ttl(self) -> Path:
        return self.root / "analysis_marker_lock" / "dlp_ttl_marker_locked.csv"


@dataclass(frozen=True)
class StimulusData:
    updates: np.ndarray  # [stimulus update, 225], digital -1/+1
    update_start_display_frame_idx: np.ndarray  # [stimulus update]
    display_frame_count: int
    recipe: dict


@dataclass(frozen=True)
class ResponseData:
    values: np.ndarray  # [imaging frame, ROI], raw mean intensity
    roi_labels: tuple[str, ...]
    original_frame_index_zero_based: np.ndarray  # [imaging frame]


@dataclass(frozen=True)
class ClockData:
    locked_dlp_time_us: np.ndarray  # [display frame]
    zeiss_frame_out_time_us: np.ndarray  # [imaging frame]
    playback_flip_time_s: np.ndarray  # [display frame], separate clock


@dataclass
class AlignedSession:
    session: Session
    stimulus: np.ndarray  # stimulus update x flattened 15 x 15 pixels, values -1/+1
    update_index: np.ndarray  # one update index per included imaging frame
    response: np.ndarray  # imaging frame x ROI, unprocessed mean intensity
    roi_labels: list[str]
    imaging_time_us: np.ndarray
    update_time_us: np.ndarray
    payload_end_us: int
    qc: dict
    original_sample_index: np.ndarray | None = None  # zero-based Results.csv data row
