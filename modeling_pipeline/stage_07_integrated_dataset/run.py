"""Stage 07: Build the provenance-preserving five-fly observation table."""
from __future__ import annotations
from pathlib import Path
import shutil
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

from dm8_modeling.datasets import load_individual_datasets, build_integrated_dataset, write_integrated_manifest
from dm8_modeling.experiments.config import Phase5Config

def run(context: WorkflowContext) -> Path:
    previous = context.require_previous(7)
    config = Phase5Config.load(context.phase5_config_path)
    individuals = load_individual_datasets(context.data_root, config.feature, config.folds[0])
    integrated = build_integrated_dataset(individuals)
    out = context.stage_dir(7)
    manifest, summary = write_integrated_manifest(integrated, out,
        {"feature": config.raw["feature"], "split": config.folds[0].intervals()})
    example = save_json(out / "example_observation.json", integrated.explain_row(0))
    dataset_manifest = context.dataset_root / "integrated/manifest.json"
    dataset_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(manifest, dataset_manifest)
    return write_stage_manifest("stage_07_integrated_dataset", out, context.config,
        [previous, context.dataset_root / "individual/manifest.json", context.phase5_config_path],
        [manifest, summary, example, dataset_manifest], context.root,
        details={"observation_count": len(integrated.y), "independent_stimulus_sequences": 1})
