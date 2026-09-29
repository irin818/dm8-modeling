"""Align saved 15 Hz updates and raw ROI rows on recorded Due TTL microseconds.

Input: a fly/run session with frozen stimulus, marker-locked DLP TTL, Zeiss
frame-out TTL and Results.csv. Output: AlignedSession within payload only.
"""
from __future__ import annotations
import json
import numpy as np
from .schema import Session, SessionPaths, StimulusData, ResponseData, ClockData, AlignedSession
from .stimulus import _sha256, verify_binary_stimulus_package
from .clocks import _read_clock, _read_playback_time, associate_imaging_with_updates
from .response import _read_results

def align_session(session: Session) -> AlignedSession:
    """Use the shared Due clock: locked DLP TTL for stimulus and Zeiss TTL for ROI rows."""
    run = session.path
    paths = SessionPaths(run)
    with (paths.stimulus_package / "stim_recipe.json").open() as handle:
        recipe = json.load(handle)
    with np.load(paths.stimulus_package / "stim_realized.npz", allow_pickle=False) as package:
        stimulus_qc = verify_binary_stimulus_package(recipe, package)
        stimulus = package["stimulus_updates_rc_float32"].reshape(-1, 225)
        update_start_frame = package["update_start_display_frame_idx_int32"]
        display_count = len(package["display_frames_gray_uint8"])
    if stimulus.shape != (9000, 225) or len(update_start_frame) != len(stimulus):
        raise ValueError(f"Unexpected frozen stimulus dimensions in {run}")
    stimulus_data = StimulusData(stimulus, update_start_frame, display_count, recipe)

    locked_ttl = _read_clock(paths.locked_dlp_ttl, "timestamp_us")
    zeiss_files = list(run.glob("zeiss_ttl_*.csv"))
    if len(zeiss_files) != 1:
        raise ValueError(f"Expected exactly one Zeiss TTL CSV in {run}")
    zeiss_ttl = _read_clock(zeiss_files[0], "timestamp_us")
    response, labels = _read_results(paths.results_csv)
    response_data = ResponseData(response, tuple(labels), np.arange(len(response), dtype=np.int32))
    if len(locked_ttl) != display_count or len(zeiss_ttl) != len(response):
        raise ValueError(f"Stimulus/TTL or Results/Zeiss row-count mismatch in {run}")
    flip_time_s = _read_playback_time(run / "playback" / "stim_frames.csv")
    clock_data = ClockData(locked_ttl, zeiss_ttl, flip_time_s)
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
    update_index, in_payload = associate_imaging_with_updates(update_times, zeiss_ttl, payload_end_us)
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
        session, stimulus_data.updates, update_index[in_payload], response_data.values[in_payload], labels,
        clock_data.zeiss_frame_out_time_us[in_payload], update_times, payload_end_us, qc,
        response_data.original_frame_index_zero_based[in_payload],
    )
