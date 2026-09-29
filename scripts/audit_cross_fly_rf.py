"""Describe cross-fly spatial RF energy without treating common stimulus as independent trials."""

import argparse
import csv
import itertools
import json
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rf-quality-csv", type=Path, required=True)
    parser.add_argument("--sta-results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    quality = list(csv.DictReader(args.rf_quality_csv.open()))
    maps, counts, peaks = {}, {}, {}
    for fly in sorted({row["fly"] for row in quality}):
        kernels = list(args.sta_results_dir.glob(f"{fly}/*/baseline_kernels.npz"))
        if len(kernels) != 1:
            raise ValueError(f"Expected one STA kernel for {fly}")
        selected = {row["roi"] for row in quality if row["fly"] == fly and
                    row["rf_confidence"] == "HIGH_CONFIDENCE_RESPONSIVE"}
        with np.load(kernels[0], allow_pickle=False) as saved:
            labels = list(saved["roi_labels"])
            indices = [idx for idx, label in enumerate(labels) if label in selected]
            if not indices:
                raise ValueError(f"No high-confidence ROIs for {fly}")
            kernel = saved["full_sta"][:18, :, :, indices]
            energy = np.sum(kernel * kernel, axis=0).mean(axis=-1)
            maps[fly] = energy.ravel()
            counts[fly] = len(indices)
            peaks[fly] = list(map(int, np.unravel_index(np.argmax(energy), (15, 15))))
    pairwise = [{"fly_a": a, "fly_b": b, "spatial_energy_map_r": float(np.corrcoef(maps[a], maps[b])[0, 1])}
                for a, b in itertools.combinations(maps, 2)]
    summary = {"selected_roi_count": counts, "local_grid_peak_row_col": peaks, "pairwise": pairwise,
               "interpretation_limit": "High-confidence selection used existing test results; identical frozen stimulus and unknown ROI alignment do not establish shared biological receptive fields."}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "cross_fly_rf.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
