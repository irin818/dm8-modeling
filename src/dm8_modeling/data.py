"""Immutable saved stimulus, ROI intensity, metadata and source fingerprints."""

from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from .timing import associate_frames, read_clock


@dataclass
class Recording:
    """One fly: stimulus [update,225], technical ROI intensity [frame,ROI], us clocks."""
    fly: str
    run_id: str
    stimulus: np.ndarray
    response: np.ndarray
    update_index: np.ndarray
    frame_us: np.ndarray
    roi_indices: np.ndarray
    metadata: dict


def sha256(path: Path) -> str:
    """Hash a file without opening it for writing; used for input provenance."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_manifest(roots: dict[str, Path]) -> dict:
    """Hash every protected source file; keys retain relative paths and sizes."""
    records = {}
    for label, root in roots.items():
        if not root.is_dir():
            raise FileNotFoundError(f"Missing read-only source directory: {root}")
        for path in sorted(root.rglob("*")):
            if path.is_file():
                name = f"{label}/{path.relative_to(root).as_posix()}"
                records[name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    return records


def manifest_digest(records: dict) -> str:
    """Return a deterministic digest of file paths, sizes and content hashes."""
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def technical_roi_mask(response: np.ndarray, config: dict) -> np.ndarray:
    """Technical QC [ROI]: finite, zero fraction<0.2 and nonconstant; no RF selection."""
    return (np.isfinite(response).all(axis=0)
            & (np.mean(response == 0, axis=0) < config["max_raw_zero_fraction"])
            & (np.std(np.where(np.isfinite(response), response, 0), axis=0) > config["minimum_response_std"]))


def load_stimulus(run: Path, config: dict) -> tuple[np.ndarray, np.ndarray, int, dict]:
    """Validate frozen [9000,15,15] binary seed/digital levels; not optical power."""
    folder = run / "stimulus_package"
    recipe = json.loads((folder / "stim_recipe.json").read_text())
    if recipe.get("stimulus_family") != "binary_discrete_time":
        raise ValueError("Only the frozen binary stimulus is supported")
    with np.load(folder / "stim_realized.npz", allow_pickle=False) as package:
        updates = package["stimulus_updates_rc_float32"]
        gray = package["stimulus_updates_display_gray_uint8"]
        display = package["display_frames_gray_uint8"]
        starts = package["update_start_display_frame_idx_int32"]
        expected = np.where(np.random.RandomState(int(recipe["randomization"]["seed"]))
            .random_sample(updates.shape) < recipe["family_parameters"]["binary_bright_probability"],
            1.0, -1.0).astype(np.float32)
        dark = int(recipe["rendering"]["dark_level"])
        bright = int(recipe["rendering"]["bright_level"])
        if not 0 <= dark < bright <= 255 or gray.shape != updates.shape:
            raise ValueError("Invalid digital levels or stimulus shape")
        if (len(starts) != len(updates) or np.any(starts < 0) or np.any(starts >= len(display))
                or np.any(np.diff(starts) <= 0)):
            raise ValueError("Invalid stimulus display-frame indices")
        if (not np.array_equal(updates, expected)
                or not np.array_equal(gray, np.where(expected > 0, bright, dark).astype(np.uint8))
                or not np.array_equal(display[starts], gray)):
            raise ValueError("Saved stimulus differs from seed or digital display mapping")
        stimulus = updates.reshape(len(updates), -1).copy()
        display_count = len(display)
    if stimulus.shape != (config["stimulus_updates"], config["grid_size"] ** 2):
        raise ValueError("Unexpected stimulus update/pixel dimensions")
    return stimulus, starts, display_count, {"seed": int(recipe["randomization"]["seed"]),
        "digital_dark": dark, "digital_bright": bright, "seed_and_gray_verified": True}


def load_recordings(root: Path, config: dict) -> list[Recording]:
    """Read one fly/run per Results.csv and align payload; no historical outputs."""
    condition = root / "UV-15Hz" if (root / "UV-15Hz").is_dir() else root
    paths = sorted(condition.glob("fly*/*/Results.csv"))
    if len(paths) != config["expected_flies"] or len({p.parent.parent.name for p in paths}) != len(paths):
        raise ValueError("Expected one distinct recording per fly")
    recordings = []
    for results_path in paths:
        run = results_path.parent
        with results_path.open(newline="", encoding="utf-8-sig") as handle:
            labels = next(csv.reader(handle))[1:]
        values = np.loadtxt(results_path, delimiter=",", skiprows=1, dtype=np.float32)
        if (not labels or len(set(labels)) != len(labels) or values.ndim != 2
                or values.shape[1] != len(labels) + 1
                or not np.array_equal(values[:, 0], np.arange(1, len(values) + 1))):
            raise ValueError(f"Invalid ROI columns or frame indices: {results_path}")
        stimulus, starts, display_count, stimulus_qc = load_stimulus(run, config)
        dlp_path = run / "analysis_marker_lock/dlp_ttl_marker_locked.csv"
        zeiss_paths = list(run.glob("zeiss_ttl_*.csv"))
        if len(zeiss_paths) != 1:
            raise ValueError(f"Expected one Zeiss TTL: {run}")
        dlp = read_clock(dlp_path, "timestamp_us")
        frames = read_clock(zeiss_paths[0], "timestamp_us")
        playback_path = run / "playback/stim_frames.csv"
        playback = read_clock(playback_path, "flip_time_s", integer=False)
        if len(dlp) != display_count or len(playback) != display_count or len(frames) != len(values):
            raise ValueError(f"CSV/stimulus/TTL row-count mismatch: {run}")
        structure_path = run / "stimulus_package/stim_structure_priors.json"
        end = int(json.loads(structure_path.read_text())["planned_frame_structure"]["payload_end_frame_idx"])
        if end >= display_count or starts[-1] >= end:
            raise ValueError("Invalid saved payload boundary")
        update_index, payload = associate_frames(dlp[starts], frames, int(dlp[end]))
        response = values[payload, 1:]
        if not len(response):
            raise ValueError("No imaging frames in stimulus payload")
        selected = np.flatnonzero(technical_roi_mask(response, config))
        if not len(selected):
            raise ValueError("No technically valid ROI")
        source_paths = [results_path, dlp_path, zeiss_paths[0], playback_path, structure_path,
                        run / "stimulus_package/stim_realized.npz", run / "stimulus_package/stim_recipe.json"]
        metadata = {**stimulus_qc, "total_roi": len(labels), "technical_roi": len(selected),
            "payload_frames": int(payload.sum()), "total_frames": len(frames),
            "median_imaging_interval_us": float(np.median(np.diff(frames))),
            "median_update_interval_us": float(np.median(np.diff(dlp[starts]))),
            "source_rows_zero_based": np.flatnonzero(payload).tolist(),
            "selected_roi_labels": [labels[i] for i in selected],
            "source_sha256": {p.relative_to(run).as_posix(): sha256(p) for p in source_paths},
            "signal": "ROI_mean_image_intensity; upstream calcium processing unresolved",
            "clock": "Zeiss frame-out TTL proxy; latest marker-locked DLP update",
            "physical_wavelength_nm": None, "physical_irradiance": None}
        recordings.append(Recording(run.parent.name, run.name, stimulus, response[:, selected],
                                    update_index[payload], frames[payload], selected, metadata))
    if any(not np.array_equal(r.stimulus, recordings[0].stimulus) for r in recordings[1:]):
        raise ValueError("The graduation dataset is expected to share one frozen stimulus")
    return recordings
