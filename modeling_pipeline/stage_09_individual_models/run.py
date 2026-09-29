"""Stage 09: Fit independent pixel and Ridge baselines on shared folds."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest

from dm8_modeling.experiments.runner import run_first_round

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(9)
    out = context.stage_dir(9)
    experiment_dir = out / "experiments"
    # Independent pixel/Ridge models on identical global stimulus folds.
    run_first_round(context.phase5_config_path, context.data_root, experiment_dir,
                    model_filter={"individual_pixel", "individual_ridge"})
    summary = experiment_dir / "first_round_summary.json"
    registry = experiment_dir / "experiment_registry.csv"
    return write_stage_manifest("stage_09_individual_models", out, context.config,
        [previous, context.phase5_config_path], [summary, registry], context.root)
