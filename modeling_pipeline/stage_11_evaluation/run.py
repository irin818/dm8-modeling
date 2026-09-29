"""Stage 11: Compare saved model scores without retraining or rewriting Stage 10."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

from dm8_modeling.evaluation.comparison import compare_cross_fold

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(11)
    experiment_dir = context.stage_dir(10) / "experiments"
    # Recompute fly-aware paired summaries from already fitted test metrics.
    comparison = compare_cross_fold(experiment_dir)
    out = context.stage_dir(11)
    summary = save_json(out / "evaluation_summary.json", comparison)
    return write_stage_manifest("stage_11_evaluation", out, context.config,
        [previous, experiment_dir / "cross_fold_comparison.json"], [summary], context.root)
