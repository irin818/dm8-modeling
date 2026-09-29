"""Locate the three read-only/work-product roots and inventory experiment files.

The workspace contains an external stimulus engineering tree, immutable fly
records, and this analysis repository. Inventory metadata has no response
samples; it records file roles, shapes and parse failures without changing
the experimental directory.
"""

from __future__ import annotations

import csv
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _role(parts: tuple[str, ...], name: str) -> tuple[str, bool, str, str]:
    """Classify by path contract; uncertain interpretations stay labelled."""
    folder = parts[3] if len(parts) > 3 else ""
    if name == "Results.csv":
        return "ROI measurements", True, "Raw per-frame ROI mean intensity target", "DIRECTLY_OBSERVED"
    if name.startswith("zeiss_ttl_") and name.endswith(".csv"):
        return "Zeiss imaging", True, "Recorded microscope frame-out clock", "DIRECTLY_OBSERVED"
    if name == "stim_realized.npz":
        return "Stimulus package", True, "Frozen update and display-frame arrays", "DIRECTLY_OBSERVED"
    if folder == "stimulus_package":
        used = name in {"stim_recipe.json", "stim_structure_priors.json"}
        return "Stimulus package", used, "Design, realized package, or package provenance", "DIRECTLY_OBSERVED"
    if folder == "playback":
        return "Playback", name == "stim_frames.csv", "Display playback plan, actual flip log, or status", "DIRECTLY_OBSERVED"
    if folder == "capture" or name.startswith("dlp_ttl_"):
        category = "DLP timing" if "dlp_ttl" in name else "Calibration" if "optical" in name else "QC"
        return category, False, "Recorded device timing, optical trace, or capture quality", "DIRECTLY_OBSERVED"
    if folder == "analysis_marker_lock":
        return "Marker lock", name in {"dlp_ttl_marker_locked.csv", "marker_lock_summary.json"}, "Marker-aligned display clock or diagnostic", "DIRECTLY_OBSERVED"
    if folder == "analysis_alignment":
        return "Calibration", name == "analysis_summary.json", "Optical/timing alignment analysis", "DIRECTLY_OBSERVED"
    if folder == "offsite_analysis":
        return "Existing analysis", name == "offsite_reference_summary.json", "Earlier RF, normalized adapter output, or reference plot", "DIRECTLY_OBSERVED"
    if name == "preflight_checklist.json":
        return "Experimental metadata", True, "DLP and acquisition preflight settings", "DIRECTLY_OBSERVED"
    if name == "preflight_checklist.md":
        return "Experimental metadata", False, "Human-readable acquisition preflight checklist", "DIRECTLY_OBSERVED"
    if name == "task3_live_qc_summary.json":
        return "QC", True, "Live acquisition quality flags", "DIRECTLY_OBSERVED"
    if name.endswith(".DS_Store"):
        return "Temporary/generated", False, "macOS Finder metadata", "DIRECTLY_OBSERVED"
    if name.startswith("session_") or name.startswith("run_manifest") or name == "microscope_play_manifest.json":
        return "Experimental metadata", False, "Run bundle, microscope schedule, or source-path metadata", "DIRECTLY_OBSERVED"
    if folder == "logs":
        return "QC", False, "Operator and acquisition event log", "DIRECTLY_OBSERVED"
    return "Unknown", False, "Requires manual provenance review", "UNRESOLVED"


def _csv_metadata(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        count = 0
        nonempty = [0] * len(columns)
        numeric = [0] * len(columns)
        minima = [float("inf")] * len(columns)
        maxima = [float("-inf")] * len(columns)
        for row in reader:
            count += 1
            if len(row) != len(columns):
                raise ValueError(f"Row {count} has {len(row)} rather than {len(columns)} columns")
            for idx, value in enumerate(row):
                if not value.strip():
                    continue
                nonempty[idx] += 1
                try:
                    number = float(value)
                except ValueError:
                    continue
                if np.isfinite(number):
                    numeric[idx] += 1
                    minima[idx] = min(minima[idx], number)
                    maxima[idx] = max(maxima[idx], number)
    numeric_ranges = {
        (column or f"column_{idx}"): [minima[idx], maxima[idx]]
        for idx, column in enumerate(columns)
        if numeric[idx] == count and count > 0
    }
    return {"columns": columns, "row_count": count, "numeric_ranges": numeric_ranges,
            "nonempty_counts": dict(zip(columns, nonempty, strict=True))}


def _json_metadata(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if isinstance(value, dict):
        return {"top_level_keys": list(value), "nested_keys": {
            key: list(child) for key, child in value.items() if isinstance(child, dict)
        }}
    return {"json_type": type(value).__name__, "length": len(value) if isinstance(value, list) else None}


def _npz_metadata(path: Path) -> dict:
    arrays = {}
    with np.load(path, allow_pickle=False) as archive:
        for name in archive.files:
            array = archive[name]
            entry = {"shape": list(array.shape), "dtype": str(array.dtype)}
            if array.size and np.issubdtype(array.dtype, np.number):
                entry["min"] = float(np.nanmin(array))
                entry["max"] = float(np.nanmax(array))
            arrays[name] = entry
    return {"arrays": arrays}


def _png_metadata(path: Path) -> dict:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("Invalid PNG signature or IHDR")
    width, height = struct.unpack(">II", header[16:24])
    return {"width": width, "height": height}


def scan_data_inventory(data_root: Path) -> list[dict]:
    """Read every file under Dm8_module, preserving its original structure."""
    root = data_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root)
        parts = relative.parts
        fly = next((part for part in parts if part.startswith("fly") and part[3:].isdigit()), None)
        run = next((part for part in parts if len(part) == 15 and part[8] == "_" and part[:8].isdigit()), None)
        category, used, role, evidence = _role(parts, path.name)
        item = {
            "relative_path": relative.as_posix(), "fly": fly, "run": run,
            "filename": path.name, "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size, "sha256": _file_sha256(path),
            "file_category": category, "currently_used_by_pipeline": used,
            "known_function": role, "possible_relevance": role,
            "evidence_status": evidence,
        }
        try:
            if path.suffix.lower() == ".csv":
                item["metadata"] = _csv_metadata(path)
                item["parse_status"] = "PARSED"
            elif path.suffix.lower() == ".json":
                item["metadata"] = _json_metadata(path)
                item["parse_status"] = "PARSED"
            elif path.suffix.lower() == ".npz":
                item["metadata"] = _npz_metadata(path)
                item["parse_status"] = "PARSED"
            elif path.suffix.lower() == ".png":
                item["metadata"] = _png_metadata(path)
                item["parse_status"] = "PARSED"
            elif path.suffix.lower() in {".md", ".log", ".jsonl", ".signal"}:
                with path.open(encoding="utf-8-sig") as handle:
                    handle.read(1024)
                item["metadata"] = {}
                item["parse_status"] = "TEXT_READABLE"
            else:
                item["metadata"] = {}
                item["parse_status"] = "UNSUPPORTED"
        except (OSError, ValueError, UnicodeError, KeyError, EOFError) as error:
            item["metadata"] = {}
            item["parse_status"] = "ERROR"
            item["parse_error"] = str(error)
        entries.append(item)
    return entries


def write_inventory(entries: list[dict], output_dir: Path) -> tuple[Path, Path]:
    """Write metadata-only JSON and a concise Markdown table outside raw data."""
    from collections import Counter

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "data_inventory.json"
    markdown_path = output_dir / "data_inventory.md"
    json_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    categories = Counter(item["file_category"] for item in entries)
    statuses = Counter(item["parse_status"] for item in entries)
    lines = ["# Dm8_module 文件清单", "", f"文件总数：{len(entries)}。解析状态：{dict(statuses)}。", "",
             "| 类别 | 文件数 |", "|---|---:|"]
    lines += [f"| {name} | {count} |" for name, count in sorted(categories.items())]
    lines += ["", "完整逐文件记录在同目录 `data_inventory.json`，包含相对路径、fly/run、大小、哈希、角色、解析状态及格式元数据。",
              "", "| 相对路径 | 类别 | 使用中 | 解析状态 | 大小 (bytes) |", "|---|---|---|---|---:|"]
    lines += [f"| `{item['relative_path']}` | {item['file_category']} | {'是' if item['currently_used_by_pipeline'] else '否'} | {item['parse_status']} | {item['size_bytes']} |" for item in entries]
    markdown_path.write_text("\n".join(lines) + "\n")
    return json_path, markdown_path
