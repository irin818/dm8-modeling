"""Long-format biological observations over one indexed frozen stimulus.

Logical row = (fly, run, ROI, imaging frame) -> (causal X, y). To avoid an
approximately 7 GB duplicate design, X is an indexed view of the common
feature table [unique update,feature]. All per-observation provenance is kept
in aligned arrays. The five flies add biological repeats, not five random
stimulus sequences. Raw experimental files remain untouched.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .individual import IndividualDataset
from .splits import SPLIT_NAMES


@dataclass(frozen=True)
class IndexedFeatureMatrix:
    table: np.ndarray
    row_index: np.ndarray

    @property
    def shape(self) -> tuple[int, int]:
        return len(self.row_index), self.table.shape[1]

    def __getitem__(self, rows: int | slice | np.ndarray | tuple) -> np.ndarray:
        if isinstance(rows, tuple):
            observation_rows, feature_columns = rows
            return self.table[self.row_index[observation_rows], feature_columns]
        return self.table[self.row_index[rows]]

    def materialize(self, max_bytes: int = 512_000_000) -> np.ndarray:
        estimated = int(np.prod(self.shape)) * self.table.dtype.itemsize
        if estimated > max_bytes:
            raise MemoryError(f"Long-format X would use {estimated:,} bytes; index only the rows needed")
        return self.table[self.row_index]


@dataclass(frozen=True)
class IntegratedDataset:
    X: IndexedFeatureMatrix  # logical [observation, feature]
    y: np.ndarray  # [observation], raw/declared transformed intensity
    fly_code: np.ndarray  # [observation]
    run_code: np.ndarray  # [observation]
    roi_index: np.ndarray  # [observation], within run
    global_roi_index: np.ndarray  # [observation], across all runs
    imaging_time_us: np.ndarray  # [observation]
    stimulus_update_index: np.ndarray  # [observation]
    session_sample_index: np.ndarray  # [observation], zero-based Results.csv data row
    split_label: np.ndarray  # [observation], global stimulus-based code
    fly_levels: tuple[str, ...]
    run_levels: tuple[str, ...]
    roi_levels: tuple[tuple[str, str, str], ...]  # (fly, run, original ROI label)
    response_kind: str
    preprocessing_kind: str
    source_hashes: dict[str, dict[str, str]]

    @property
    def fly_id(self) -> np.ndarray:
        return np.asarray(self.fly_levels)[self.fly_code]

    @property
    def run_id(self) -> np.ndarray:
        return np.asarray(self.run_levels)[self.run_code]

    @property
    def roi_id(self) -> np.ndarray:
        return np.asarray([key[2] for key in self.roi_levels])[self.global_roi_index]

    @property
    def unique_stimulus_update_count(self) -> int:
        return int(np.unique(self.stimulus_update_index).size)

    def explain_row(self, row: int) -> dict:
        """Trace one y value back to its original fly/run/ROI/Results.csv row."""
        if not 0 <= row < len(self.y):
            raise IndexError(row)
        roi = self.roi_levels[int(self.global_roi_index[row])]
        return {"fly_id": roi[0], "run_id": roi[1], "roi_id": roi[2],
                "roi_index": int(self.roi_index[row]),
                "session_sample_index_zero_based": int(self.session_sample_index[row]),
                "Results_csv_frame_one_based": int(self.session_sample_index[row] + 1),
                "imaging_time_us": int(self.imaging_time_us[row]),
                "stimulus_update_index": int(self.stimulus_update_index[row]),
                "response": float(self.y[row]), "response_kind": self.response_kind,
                "preprocessing_kind": self.preprocessing_kind,
                "split_label": SPLIT_NAMES[int(self.split_label[row])],
                "feature_shape": [int(self.X.shape[1])],
                "source_hashes": self.source_hashes[roi[0]]}


def build_integrated_dataset(
    individuals: list[IndividualDataset], responses: dict[str, np.ndarray] | None = None,
    response_kind: str = "unprocessed_ROI_mean_intensity", preprocessing_kind: str = "raw",
) -> IntegratedDataset:
    """Create one provenance-preserving long table with indexed common X."""
    if not individuals or len({item.fly_id for item in individuals}) != len(individuals):
        raise ValueError("Expected distinct fly datasets")
    table = individuals[0].feature_table
    if any(item.feature_table is not table for item in individuals[1:]):
        raise ValueError("Individuals must share the same verified feature table")
    chunks: dict[str, list[np.ndarray]] = {key: [] for key in (
        "y", "fly_code", "run_code", "roi_index", "global_roi_index", "imaging_time_us",
        "stimulus_update_index", "session_sample_index", "split_label", "feature_row")}
    roi_levels = []
    source_hashes = {}
    feature_origin = individuals[0].feature_definition.history_updates - 1
    for fly_number, item in enumerate(individuals):
        y = item.y_raw if responses is None else responses[item.fly_id]
        if y.shape != item.y_raw.shape or not np.isfinite(y).all():
            raise ValueError(f"Invalid processed response shape or values for {item.fly_id}")
        n_frame, n_roi = y.shape
        row_index = np.repeat(np.arange(n_frame), n_roi)
        roi_index = np.tile(np.arange(n_roi), n_frame)
        chunks["y"].append(y.reshape(-1).astype(np.float32))
        chunks["fly_code"].append(np.full(n_frame * n_roi, fly_number, dtype=np.uint8))
        chunks["run_code"].append(np.full(n_frame * n_roi, fly_number, dtype=np.uint8))
        chunks["roi_index"].append(roi_index.astype(np.int16))
        chunks["global_roi_index"].append((roi_index + len(roi_levels)).astype(np.int16))
        for key, values in (("imaging_time_us", item.imaging_time_us),
                            ("stimulus_update_index", item.update_index),
                            ("session_sample_index", item.original_sample_index),
                            ("split_label", item.split_label),
                            ("feature_row", item.update_index - feature_origin)):
            chunks[key].append(values[row_index])
        roi_levels.extend((item.fly_id, item.run_id, label) for label in item.roi_labels)
        source_hashes[item.fly_id] = dict(item.aligned.qc["source_sha256"])
    arrays = {key: np.concatenate(values) for key, values in chunks.items()}
    return IntegratedDataset(
        IndexedFeatureMatrix(table, arrays.pop("feature_row")),
        arrays["y"], arrays["fly_code"], arrays["run_code"], arrays["roi_index"],
        arrays["global_roi_index"], arrays["imaging_time_us"], arrays["stimulus_update_index"],
        arrays["session_sample_index"], arrays["split_label"],
        tuple(item.fly_id for item in individuals), tuple(item.run_id for item in individuals),
        tuple(roi_levels), response_kind, preprocessing_kind, source_hashes,
    )


def write_integrated_manifest(dataset: IntegratedDataset, output_dir: Path, config: dict) -> tuple[Path, Path]:
    """Save only metadata and counts; never duplicate raw or long X arrays."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "integrated_dataset_manifest.json"
    summary_path = output_dir / "integrated_dataset_summary.csv"
    roi_counts = np.bincount(dataset.global_roi_index, minlength=len(dataset.roi_levels))
    fly_counts = np.bincount(dataset.fly_code, minlength=len(dataset.fly_levels))
    split_counts = np.bincount(dataset.split_label, minlength=len(SPLIT_NAMES))
    manifest = {
        "schema_version": "phase5_integrated_v1", "representation": "long_format_indexed_shared_X",
        "observation_count": len(dataset.y), "fly_count": len(dataset.fly_levels),
        "roi_count": len(dataset.roi_levels),
        "unique_stimulus_update_count": dataset.unique_stimulus_update_count,
        "independent_random_stimulus_sequences": 1,
        "logical_X_shape": list(dataset.X.shape), "feature_table_shape": list(dataset.X.table.shape),
        "response_kind": dataset.response_kind, "preprocessing_kind": dataset.preprocessing_kind,
        "split_observation_counts": dict(zip(SPLIT_NAMES, map(int, split_counts), strict=True)),
        "fly_observation_counts": dict(zip(dataset.fly_levels, map(int, fly_counts), strict=True)),
        "source_sha256_by_fly": dataset.source_hashes, "config": config,
        "provenance_note": "One logical row is a fly/run/ROI/Results.csv frame. Five flies share one frozen stimulus; observation count is not independent stimulus count.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["fly_id", "run_id", "roi_id", "observation_count"])
        writer.writeheader()
        for (fly, run, roi), count in zip(dataset.roi_levels, roi_counts, strict=True):
            writer.writerow({"fly_id": fly, "run_id": run, "roi_id": roi, "observation_count": int(count)})
    return manifest_path, summary_path
