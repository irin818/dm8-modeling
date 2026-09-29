"""Stage 06: individual dataset. Orchestrate existing source APIs; do not implement algorithms here."""
from __future__ import annotations
import json
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json, save_csv

import numpy as np
from dm8_modeling.datasets import load_individual_datasets
from dm8_modeling.datasets.splits import TRAIN, VALIDATION, TEST
from dm8_modeling.experiments.config import Phase5Config

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(6)
    config = Phase5Config.load(context.phase5_config_path)
    individuals = load_individual_datasets(context.data_root, config.feature, config.folds[0])
    rows = [{"fly_id": item.fly_id, "run_id": item.run_id, "roi_count": len(item.roi_labels),
             "X_shape": list(item.X.shape), "y_shape": list(item.y_raw.shape),
             "train_frames": int(np.sum(item.split_label == TRAIN)),
             "validation_frames": int(np.sum(item.split_label == VALIDATION)),
             "test_frames": int(np.sum(item.split_label == TEST)),
             "source_sha256": item.aligned.qc["source_sha256"]} for item in individuals]
    out = context.stage_dir(6)
    summary = save_json(out / "individual_datasets.json", rows)
    dataset_manifest = save_json(context.dataset_root / "individual/manifest.json",
        {"definition": "one fly/run per IndividualDataset", "fold": config.folds[0].name,
         "datasets": rows, "raw_data_copied": False})
    return write_stage_manifest("stage_06_individual_dataset", out, context.config,
                                [previous, context.phase5_config_path],
                                [summary, dataset_manifest], context.root)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(run(WorkflowContext.load(args.workspace_root)))
