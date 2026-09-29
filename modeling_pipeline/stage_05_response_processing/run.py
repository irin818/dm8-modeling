"""Stage 05: Describe causal response processing and training-only scaling."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

import numpy as np
from dm8_modeling.data import align_session, discover_sessions
from dm8_modeling.datasets.splits import TRAIN
from dm8_modeling.experiments.config import Phase5Config
from dm8_modeling.preprocessing import candidate_response, fit_response_scaler

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(5)
    config = Phase5Config.load(context.phase5_config_path)
    kind = config.raw["response"]["primary_kind"]
    normalization = config.raw["response"]["primary_normalization"]
    rows = []
    for session in discover_sessions(context.data_root):
        aligned = align_session(session)
        response = candidate_response(aligned.response, aligned.imaging_time_us, kind)
        eligible = aligned.update_index >= config.feature.history_updates - 1
        labels = config.folds[0].labels(aligned.update_index[eligible], len(aligned.stimulus))
        scaler = fit_response_scaler(response[eligible], labels == TRAIN, normalization)
        rows.append({"fly_id": session.fly, "response_kind": kind,
                     "eligible_response_shape": list(response[eligible].shape),
                     "train_frames": int(np.sum(labels == TRAIN)),
                     "median_train_scale": float(np.median(scaler.scale)),
                     "zero_variance_roi_count": int(np.sum(scaler.zero_variance_roi)),
                     "normalization": scaler.normalization})
    out = context.stage_dir(5)
    summary = save_json(out / "response_processing_summary.json", rows)
    return write_stage_manifest("stage_05_response_processing", out, context.config,
                                [previous, context.phase5_config_path], [summary], context.root)
