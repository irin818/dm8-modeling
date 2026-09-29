"""Stage 11: evaluation. Orchestrate existing source APIs; do not implement algorithms here."""
from __future__ import annotations
import json
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json, save_csv

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


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(WorkflowContext.load(args.workspace_root)))
