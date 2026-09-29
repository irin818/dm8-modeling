"""Stage 04: Align imaging frames to already-presented stimulus updates."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

from dm8_modeling.data import align_session, discover_sessions

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(4)
    rows = []
    for session in discover_sessions(context.data_root):
        aligned = align_session(session)
        rows.append({"fly_id": session.fly, "run_id": session.run_id,
                     "aligned_response_shape": list(aligned.response.shape),
                     "stimulus_shape": list(aligned.stimulus.shape),
                     "first_update": int(aligned.update_index[0]),
                     "last_update": int(aligned.update_index[-1]),
                     "first_original_result_row_zero_based": int(aligned.original_sample_index[0]),
                     "payload_end_us_exclusive": aligned.payload_end_us, "qc": aligned.qc})
    out = context.stage_dir(4)
    summary = save_json(out / "aligned_sessions.json", rows)
    return write_stage_manifest("stage_04_alignment", out, context.config,
                                [previous], [summary], context.root, details={"aligned_fly_count": len(rows)})
