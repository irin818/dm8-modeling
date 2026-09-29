"""Ordered workflow execution with explicit predecessor receipts.

Stage orchestration lives in modeling_pipeline/stage_*/run.py. This module
only resolves roots, validates predecessor manifests, and dispatches a stage.
"""
from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

from ..io.stage_manifest import verify_stage_manifest


STAGE_NAMES = (
    "stage_01_source_audit", "stage_02_stimulus", "stage_03_response_and_clocks",
    "stage_04_alignment", "stage_05_response_processing", "stage_06_individual_dataset",
    "stage_07_integrated_dataset", "stage_08_rf_recovery", "stage_09_individual_models",
    "stage_10_population_models", "stage_11_evaluation", "stage_12_final_analysis",
)


@dataclass(frozen=True)
class WorkflowContext:
    root: Path
    config: dict

    @classmethod
    def load(cls, root: Path) -> "WorkflowContext":
        root = root.expanduser().resolve()
        config = json.loads((root / "configs" / "workflow.json").read_text())
        if config.get("schema_version") != "workflow_v1":
            raise ValueError("Unsupported workflow config")
        return cls(root, config)

    @property
    def data_root(self) -> Path:
        return self.root / self.config["data_root"]

    @property
    def stimulus_code_root(self) -> Path:
        return self.root / self.config["stimulus_code_root"]

    @property
    def output_root(self) -> Path:
        return self.root / self.config["output_root"]

    @property
    def dataset_root(self) -> Path:
        return self.root / self.config["dataset_root"]

    @property
    def phase5_config_path(self) -> Path:
        return self.root / self.config["phase5_experiment_config"]

    def stage_dir(self, number: int) -> Path:
        return self.output_root / STAGE_NAMES[number - 1]

    def require_previous(self, number: int) -> Path | None:
        if number == 1:
            return None
        previous = self.stage_dir(number - 1) / "stage_manifest.json"
        verify_stage_manifest(previous, self.config)
        return previous


def run_stage(number: int, context: WorkflowContext) -> Path:
    """Run exactly one stage; never execute missing earlier stages implicitly."""
    if number < 1 or number > len(STAGE_NAMES):
        raise ValueError("Stage number must be 1 through 12")
    context.require_previous(number)
    path = context.root / "modeling_pipeline" / STAGE_NAMES[number - 1] / "run.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(f"dm8_workflow_stage_{number:02d}", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = module.run(context)
    verify_stage_manifest(manifest, context.config)
    return manifest
