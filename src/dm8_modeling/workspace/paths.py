"""Resolve read-only experimental roots and derived-output path contracts."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    data_root: Path
    stimulus_code_root: Path
    output_dir: Path

    @classmethod
    def resolve(
        cls,
        workspace_root: Path,
        data_root: Path | None = None,
        stimulus_code_root: Path | None = None,
        output_dir: Path | None = None,
    ) -> "WorkspacePaths":
        root = workspace_root.expanduser().resolve()
        data = (data_root or root / "Dm8_module").expanduser().resolve()
        code = (stimulus_code_root or root / "simulate").expanduser().resolve()
        output = (output_dir or root / "outputs" / "audit").expanduser().resolve()
        if not root.is_dir() or not data.is_dir() or not code.is_dir():
            raise FileNotFoundError("Workspace, Dm8_module, or simulate directory is missing")
        if not any(data.glob("UV-15Hz/fly*/*/Results.csv")) and not any(data.glob("fly*/*/Results.csv")):
            raise FileNotFoundError(f"No experimental Results.csv under {data}")
        return cls(root, data, code, output)
