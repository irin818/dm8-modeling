"""Record stage provenance without copying raw experiment arrays.

Input and output paths are hashed as files; raw directories remain read-only.
The manifest binds each workflow stage to its config and Git revision.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_hashes(paths: list[Path]) -> dict[str, str]:
    result = {}
    for path in paths:
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        result[str(resolved)] = _sha256(resolved)
    return result


def write_stage_manifest(stage_name: str, output_dir: Path, config: dict,
                         inputs: list[Path], outputs: list[Path], root: Path,
                         status: str = "complete", details: dict | None = None) -> Path:
    """Save a stage receipt with SHA-256 for all declared input/output files."""
    if status not in {"complete", "failed"}:
        raise ValueError("Unknown stage status")
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                                         stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    payload = {"schema_version": "dm8_stage_manifest_v1", "stage_name": stage_name,
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "input_paths": [str(path.resolve()) for path in inputs],
               "input_hashes": _file_hashes(inputs),
               "config": config,
               "outputs": [str(path.resolve()) for path in outputs],
               "output_hashes": _file_hashes(outputs),
               "git_commit_sha": commit, "status": status, "details": details or {}}
    path = output_dir / "stage_manifest.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    return path


def verify_stage_manifest(path: Path, config: dict) -> dict:
    """Require the predecessor to be complete and its declared files unchanged."""
    if not path.is_file():
        raise FileNotFoundError(f"Run the previous stage first: missing {path}")
    payload = json.loads(path.read_text())
    if payload.get("status") != "complete":
        raise ValueError(f"Previous stage is not complete: {path}")
    if payload.get("config") != config:
        raise ValueError(f"Previous stage used different workflow config: {path}")
    for label in ("input_hashes", "output_hashes"):
        for name, expected in payload[label].items():
            target = Path(name)
            if not target.is_file() or _sha256(target) != expected:
                raise ValueError(f"Previous stage {label} changed: {target}")
    return payload
