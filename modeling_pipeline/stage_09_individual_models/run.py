"""Stage 09: individual models. Orchestrate existing source APIs; do not implement algorithms here."""
from __future__ import annotations
import json
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json, save_csv

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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(WorkflowContext.load(args.workspace_root)))
