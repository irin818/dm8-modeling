"""Stage 12: final analysis. Orchestrate existing source APIs; do not implement algorithms here."""
from __future__ import annotations
import json
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json, save_csv


def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(12)
    evaluation = json.loads((context.stage_dir(11) / "evaluation_summary.json").read_text())
    report = context.root / "docs/FINAL_PREDICTIVE_MODEL_REPORT.md"
    if not report.is_file():
        raise FileNotFoundError(report)
    out = context.stage_dir(12)
    summary = save_json(out / "final_analysis.json",
        {"stopping_decision": "STOP_B", "scientific_report": str(report),
         "independent_stimulus_sequences": 1,
         "evaluated_models": list(evaluation["folds"]["fold_a"]),
         "interpretation": "Historical exploratory tests; shared models do not consistently beat independent models."})
    return write_stage_manifest("stage_12_final_analysis", out, context.config,
                                [previous, report], [summary], context.root)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(WorkflowContext.load(args.workspace_root)))
