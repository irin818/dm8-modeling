"""Stage 03: Summarize raw ROI intensities and recorded clocks."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

from dm8_modeling.data import SessionPaths, discover_sessions, load_response_data, load_clock_data

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(3)
    rows, inputs = [], [previous]
    for session in discover_sessions(context.data_root):
        paths = SessionPaths(session.path)
        response = load_response_data(paths)
        clocks, zeiss_path = load_clock_data(paths)
        if len(response.values) != len(clocks.zeiss_frame_out_time_us):
            raise ValueError(f"Results/Zeiss frame mismatch: {session.fly}")
        rows.append({"fly_id": session.fly, "run_id": session.run_id,
                     "response_shape": list(response.values.shape), "roi_labels": list(response.roi_labels),
                     "zeiss_frames": len(clocks.zeiss_frame_out_time_us),
                     "dlp_frames": len(clocks.locked_dlp_time_us),
                     "playback_frames": len(clocks.playback_flip_time_s),
                     "response_kind": "raw_ROI_mean_intensity", "ttl_unit": "microseconds"})
        inputs += [paths.results_csv, zeiss_path, paths.locked_dlp_ttl,
                   paths.root / "playback/stim_frames.csv"]
    out = context.stage_dir(3)
    summary = save_json(out / "response_clock_summary.json", rows)
    return write_stage_manifest("stage_03_response_and_clocks", out, context.config, inputs, [summary], context.root)
