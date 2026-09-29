"""Stage 01: Inventory immutable experiment files and stimulus source code."""
from __future__ import annotations
from pathlib import Path
from dm8_modeling.experiments.workflow import WorkflowContext
from dm8_modeling.io.stage_manifest import write_stage_manifest
from dm8_modeling.io.tables import save_json

from dm8_modeling.workspace import scan_data_inventory, write_inventory

def run(context: WorkflowContext) -> Path:
    # 1. Audit immutable experimental files and their metadata.
    entries = scan_data_inventory(context.data_root)
    out = context.stage_dir(1)
    inventory_json, inventory_md = write_inventory(entries, out)
    # 2. Index the local stimulus engineering copy without altering it.
    scripts = sorted(context.stimulus_code_root.rglob("*.py"))
    source_index = save_json(out / "stimulus_source_index.json",
        {"python_file_count": len(scripts), "files": [str(path.relative_to(context.root)) for path in scripts]})
    source_files = [context.data_root / entry["relative_path"] for entry in entries]
    return write_stage_manifest("stage_01_source_audit", out, context.config,
        [context.root / "configs/workflow.json", *source_files, *scripts],
        [inventory_json, inventory_md, source_index], context.root,
        details={"experimental_file_count": len(entries), "stimulus_source_python_files": len(scripts)})
