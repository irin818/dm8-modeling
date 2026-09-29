"""Read the frozen stimulus and recorded clocks without editing experiment files."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Session:
    path: Path
    fly: str
    run_id: str


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


def discover_sessions(root: Path) -> list[Session]:
    """Find recorded sessions in either Dm8_module or UV-15Hz."""
    root = root.expanduser().resolve()
    condition = root / "UV-15Hz" if (root / "UV-15Hz").is_dir() else root
    sessions = []
    for results in sorted(condition.glob("fly*/*/Results.csv")):
        run = results.parent
        sessions.append(Session(run, run.parent.name, run.name))
    if not sessions:
        raise FileNotFoundError(f"No fly*/<run>/Results.csv sessions found under {root}")
    return sessions


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def verify_binary_stimulus_package(recipe: dict, package: dict[str, np.ndarray]) -> dict:
    """Check the saved binary sequence against its own seed and digital levels."""
    if recipe.get("stimulus_family") != "binary_discrete_time":
        raise ValueError("Only binary_discrete_time stimulus packages are supported")
    updates = package["stimulus_updates_rc_float32"]
    gray = package["stimulus_updates_display_gray_uint8"]
    display = package["display_frames_gray_uint8"]
    start = package["update_start_display_frame_idx_int32"]
    rendering = recipe["rendering"]
    dark, bright = int(rendering["dark_level"]), int(rendering["bright_level"])
    if not 0 <= dark < bright <= 255 or updates.shape != gray.shape:
        raise ValueError("Invalid digital gray levels or update shapes")
    probability = float(recipe["family_parameters"]["binary_bright_probability"])
    if not 0 <= probability <= 1:
        raise ValueError("Invalid binary bright probability")
    expected = np.where(
        np.random.RandomState(int(recipe["randomization"]["seed"]))
        .random_sample(updates.shape) < probability,
        1.0, -1.0,
    ).astype(np.float32)
    expected_gray = np.where(expected > 0, bright, dark).astype(np.uint8)
    if len(start) != len(updates) or np.any(start < 0) or np.any(start >= len(display)):
        raise ValueError("Invalid display-frame indices for stimulus updates")
    if not np.array_equal(updates, expected):
        raise ValueError("Frozen binary stimulus differs from recipe seed reconstruction")
    if not np.array_equal(gray, expected_gray):
        raise ValueError("Frozen stimulus digital gray does not match ±1 coding")
    if not np.array_equal(display[start], gray):
        raise ValueError("Display frames differ from frozen update gray levels")
    return {
        "seed_reconstruction_passed": True,
        "digital_gray_mapping_passed": True,
        "minus_one_commanded_gray": dark,
        "plus_one_commanded_gray": bright,
        "digital_color_channel": str(rendering["color_channel"]),
        "stimulus_seed": int(recipe["randomization"]["seed"]),
        "nominal_pixel_width_deg": float(recipe["geometry"]["summary"]["derived"]["actual_cell_width_deg"]),
        "nominal_pixel_height_deg": float(recipe["geometry"]["summary"]["derived"]["actual_cell_height_deg"]),
    }


def align_session(session: Session) -> AlignedSession:
    """Use the shared Due clock: locked DLP TTL for stimulus and Zeiss TTL for ROI rows."""
    run = session.path
    with (run / "stimulus_package" / "stim_recipe.json").open() as handle:
        recipe = json.load(handle)
    with np.load(run / "stimulus_package" / "stim_realized.npz", allow_pickle=False) as package:
        stimulus_qc = verify_binary_stimulus_package(recipe, package)
        stimulus = package["stimulus_updates_rc_float32"].reshape(-1, 225)
        update_start_frame = package["update_start_display_frame_idx_int32"]
        display_count = len(package["display_frames_gray_uint8"])
    if stimulus.shape != (9000, 225) or len(update_start_frame) != len(stimulus):
        raise ValueError(f"Unexpected frozen stimulus dimensions in {run}")

    locked_ttl = _read_clock(run / "analysis_marker_lock" / "dlp_ttl_marker_locked.csv", "timestamp_us")
    zeiss_files = list(run.glob("zeiss_ttl_*.csv"))
    if len(zeiss_files) != 1:
        raise ValueError(f"Expected exactly one Zeiss TTL CSV in {run}")
    zeiss_ttl = _read_clock(zeiss_files[0], "timestamp_us")
    response, labels = _read_results(run / "Results.csv")
    if len(locked_ttl) != display_count or len(zeiss_ttl) != len(response):
        raise ValueError(f"Stimulus/TTL or Results/Zeiss row-count mismatch in {run}")
    flip_time_s = _read_playback_time(run / "playback" / "stim_frames.csv")
    if len(flip_time_s) != display_count:
        raise ValueError(f"Playback row count does not match frozen stimulus in {run}")
    if np.any(np.diff(update_start_frame) <= 0):
        raise ValueError(f"Stimulus update frames are not strictly increasing in {run}")

    with (run / "stimulus_package" / "stim_structure_priors.json").open() as handle:
        structure = json.load(handle)["planned_frame_structure"]
    payload_end_frame = int(structure["payload_end_frame_idx"])
    if payload_end_frame >= display_count or update_start_frame[-1] >= payload_end_frame:
        raise ValueError(f"Invalid payload boundary in {run}")
    update_times = locked_ttl[update_start_frame]
    payload_end_us = int(locked_ttl[payload_end_frame])
    # Exposure time within a Zeiss frame is not supplied. Frame-out TTL is the declared proxy.
    update_index = np.searchsorted(update_times, zeiss_ttl, side="right") - 1
    in_payload = (update_index >= 0) & (zeiss_ttl < payload_end_us)
    if not np.any(in_payload):
        raise ValueError(f"No Zeiss frames overlap the recorded stimulus payload in {run}")

    with (run / "task3_live_qc_summary.json").open() as handle:
        acquisition_qc = json.load(handle)
    with (run / "analysis_marker_lock" / "marker_lock_summary.json").open() as handle:
        lock_qc = json.load(handle)
    with (run / "analysis_alignment" / "analysis_summary.json").open() as handle:
        optical_alignment = json.load(handle)
    with (run / "offsite_analysis" / "ref" / "offsite_reference_summary.json").open() as handle:
        reference_summary = json.load(handle)
    with (run / "preflight_checklist.json").open() as handle:
        preflight = json.load(handle)
    dlp_sections = [item for item in preflight["sections"] if item["section_name"] == "DLP GUI"]
    if len(dlp_sections) != 1:
        raise ValueError(f"Expected one DLP preflight section in {run}")
    clock_offset_s = locked_ttl / 1_000_000 - flip_time_s
    residual_ms = (clock_offset_s - np.median(clock_offset_s)) * 1000
    qc = {
        **stimulus_qc,
        "source_sha256": {
            "stim_realized.npz": _sha256(run / "stimulus_package" / "stim_realized.npz"),
            "stim_recipe.json": _sha256(run / "stimulus_package" / "stim_recipe.json"),
            "Results.csv": _sha256(run / "Results.csv"),
            "dlp_ttl_marker_locked.csv": _sha256(run / "analysis_marker_lock" / "dlp_ttl_marker_locked.csv"),
            "preflight_checklist.json": _sha256(run / "preflight_checklist.json"),
            "offsite_reference_summary.json": _sha256(run / "offsite_analysis" / "ref" / "offsite_reference_summary.json"),
            zeiss_files[0].name: _sha256(zeiss_files[0]),
        },
        "all_zeiss_frames": int(len(zeiss_ttl)),
        "payload_zeiss_frames": int(in_payload.sum()),
        "roi_count": len(labels),
        "stimulus_updates": len(stimulus),
        "display_frames": display_count,
        "median_zeiss_interval_ms": float(np.median(np.diff(zeiss_ttl)) / 1000),
        "median_display_interval_ms": float(np.median(np.diff(locked_ttl)) / 1000),
        "playback_to_dlp_offset_s": float(np.median(clock_offset_s)),
        "playback_to_dlp_p99_abs_residual_ms": float(np.quantile(np.abs(residual_ms), 0.99)),
        "zero_intensity_fraction": float(np.mean(response == 0)),
        "acquisition_qc_passed": bool(acquisition_qc["task3_live_qc_passed"]),
        "marker_lock_passed": bool(lock_qc["lock_success"]),
        "response_kind": "unprocessed_ROI_mean_intensity",
        "imaging_time_proxy": "Zeiss frame-out TTL timestamp_us",
        "stimulus_time_source": "marker-locked DLP TTL timestamp_us",
        "fly_side_orientation_calibration": reference_summary.get("canonical_orientation"),
        "preflight_dlp_light_source": dlp_sections[0]["profile"].get("light_source"),
        "marker_ttl_to_optical_latency_us": optical_alignment.get("trial_start_anchor_ttl_to_optical_latency_us"),
        "physical_wavelength_nm": None,
        "physical_irradiance": None,
    }
    return AlignedSession(
        session, stimulus, update_index[in_payload], response[in_payload], labels,
        zeiss_ttl[in_payload], update_times, payload_end_us, qc,
    )
