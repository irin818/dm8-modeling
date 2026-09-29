"""Dataset, fit, and evaluation commands for the multi-fly Phase 5 work."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .datasets import build_integrated_dataset, load_individual_datasets, write_integrated_manifest
from .experiments.config import Phase5Config
from .experiments.runner import run_first_round


MODELS = ("individual_pixel", "individual_ridge", "individual_raw_units",
          "shared_strf_affine", "shared_plus_fly_deviation", "shared_factorized_basis",
          "shared_strf_equal_roi", "shared_strf_raw_units", "population_average_ridge",
          "response_candidates", "leave_one_fly_out")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("dataset", "fit", "evaluate"))
    parser.add_argument("target", nargs="?", help="dataset: build-individual/build-integrated/describe-integrated; fit: model or all")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fold", choices=("fold_a", "fold_b"), default="fold_a")
    args = parser.parse_args(argv)
    workspace = args.workspace_root.resolve()
    config_path = args.config or workspace / "configs" / "phase5_first_round.json"
    data_root = args.data_root or workspace / "Dm8_module"
    output = args.output_dir or workspace / "outputs" / "experiments" / "phase5_first_round"
    if args.action == "fit":
        if args.target not in (None, "all", *MODELS):
            parser.error(f"fit target must be all or one of: {', '.join(MODELS)}")
        result = run_first_round(config_path, data_root, output,
                                 None if args.target in (None, "all") else {args.target})
        print(json.dumps({"output": str(output), "folds": list(result["folds"])}, ensure_ascii=False))
        return
    if args.action == "evaluate":
        summary = output / "first_round_summary.json"
        if not summary.exists():
            parser.error(f"Run fit first; missing {summary}")
        print(summary.read_text())
        return
    if args.target not in ("build-individual", "build-integrated", "describe-integrated"):
        parser.error("dataset target must be build-individual, build-integrated, or describe-integrated")
    config = Phase5Config.load(config_path)
    fold = next(split for split in config.folds if split.name == args.fold)
    individuals = load_individual_datasets(data_root, config.feature, fold)
    destination = output / fold.name / "dataset"
    destination.mkdir(parents=True, exist_ok=True)
    if args.target == "build-individual":
        rows = [{"fly_id": item.fly_id, "run_id": item.run_id,
                 "eligible_frames": len(item.y_raw), "roi_count": len(item.roi_labels),
                 "feature_shape": list(item.X.shape), "response_shape": list(item.y_raw.shape),
                 "training_frames": int(np.sum(item.split_label == 0)),
                 "validation_frames": int(np.sum(item.split_label == 1)),
                 "test_frames": int(np.sum(item.split_label == 2)),
                 "source_sha256": item.aligned.qc["source_sha256"]} for item in individuals]
        path = destination / "individual_datasets.json"
        path.write_text(json.dumps(rows, indent=2) + "\n")
        print(path)
        return
    integrated = build_integrated_dataset(individuals)
    if args.target == "build-integrated":
        paths = write_integrated_manifest(integrated, destination,
            {"feature": config.raw["feature"], "split": fold.intervals()})
        print(json.dumps({"manifest": str(paths[0]), "summary": str(paths[1]),
                          "example_row": integrated.explain_row(0)}))
    else:
        print(json.dumps({"shape": integrated.X.shape, "roi_count": len(integrated.roi_levels),
                          "fly_count": len(integrated.fly_levels),
                          "unique_stimulus_updates": integrated.unique_stimulus_update_count,
                          "example_row": integrated.explain_row(0)}, indent=2))
