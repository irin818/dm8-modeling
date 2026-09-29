"""Stage 08: Save training RF estimates and ROI reliability diagnostics."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_csv

from dm8_modeling.datasets import load_individual_datasets
from dm8_modeling.evaluation.reliability import assess_training_reliability
from dm8_modeling.experiments.config import Phase5Config
from dm8_modeling.preprocessing.normalization import process_individual_response

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(8)
    config = Phase5Config.load(context.phase5_config_path)
    individuals = load_individual_datasets(context.data_root, config.feature, config.folds[0])
    records = []
    out = context.stage_dir(8)
    out.mkdir(parents=True, exist_ok=True)
    kernel_paths = []
    for item in individuals:
        processed = process_individual_response(item, "raw", "train_zscore")
        result = assess_training_reliability(item, processed, config.raw["roi_selection"])
        records.extend(result.records())
        kernel_path = out / f"{item.fly_id}_training_rf_kernels.npz"
        np.savez_compressed(kernel_path, first_half=result.first_half_kernel,
                            second_half=result.second_half_kernel,
                            validation_diagnostic=result.validation_kernel,
                            roi_labels=np.asarray(result.roi_labels))
        kernel_paths.append(kernel_path)
    table = save_csv(out / "training_rf_reliability.csv", records)
    return write_stage_manifest("stage_08_rf_recovery", out, context.config,
        [previous, context.phase5_config_path], [table, *kernel_paths], context.root,
        details={"roi_count": len(records),
                 "train_defined_responsive_count": sum(row["train_defined_responsive"] for row in records)})
