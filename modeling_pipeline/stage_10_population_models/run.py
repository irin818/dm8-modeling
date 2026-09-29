"""Stage 10: population models. Orchestrate existing source APIs; do not implement algorithms here."""
from __future__ import annotations
import json
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json, save_csv

from dm8_modeling.experiments.runner import run_first_round

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(10)
    out = context.stage_dir(10)
    experiment_dir = out / "experiments"
    # Shared, hierarchical, low-rank, population and transfer comparisons.
    result = run_first_round(context.phase5_config_path, context.data_root, experiment_dir)
    members = {}
    for fold in result["folds"]:
        path = experiment_dir / fold / "models/population_average_ridge/members.json"
        members[fold] = json.loads(path.read_text())
    dataset_manifest = save_json(context.dataset_root / "population/manifest.json",
        {"definition": "within-fly mean of training-selected standardized ROI traces",
         "members_by_fold": members, "raw_data_copied": False})
    summary = experiment_dir / "first_round_summary.json"
    registry = experiment_dir / "experiment_registry.csv"
    comparison = experiment_dir / "cross_fold_comparison.json"
    return write_stage_manifest("stage_10_population_models", out, context.config,
        [previous, context.phase5_config_path], [summary, registry, comparison, dataset_manifest], context.root)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(WorkflowContext.load(args.workspace_root)))
