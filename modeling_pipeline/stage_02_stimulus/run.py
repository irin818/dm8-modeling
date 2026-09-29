"""Stage 02: Verify each saved stimulus package and summarize its digital commands."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

from dm8_modeling.data import SessionPaths, discover_sessions, load_stimulus_data

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(2)
    rows, inputs = [], [previous]
    for session in discover_sessions(context.data_root):
        paths = SessionPaths(session.path)
        stimulus, qc = load_stimulus_data(paths)
        rows.append({"fly_id": session.fly, "run_id": session.run_id, "updates": len(stimulus.updates),
            "pixels": stimulus.updates.shape[1], "display_frames": stimulus.display_frame_count,
            "hold_frames": int(stimulus.recipe["stimulus_timing"]["stimulus_hold_frames"]),
            "update_hz": float(stimulus.recipe["stimulus_timing"]["stimulus_update_hz_effective"]),
            "display_hz": float(stimulus.recipe["display_timing"]["display_refresh_hz"]),
            "seed_reconstruction_passed": qc["seed_reconstruction_passed"]})
        inputs += [paths.stimulus_package / "stim_recipe.json", paths.stimulus_package / "stim_realized.npz"]
    out = context.stage_dir(2)
    summary = save_json(out / "stimulus_summary.json", rows)
    return write_stage_manifest("stage_02_stimulus", out, context.config, inputs, [summary], context.root,
                                details={"shared_digital_stimulus_verified": True})
