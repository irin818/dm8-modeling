"""Fly-aware comparisons and cross-fold parameter stability from saved artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


def _read_scores(path: Path) -> dict[tuple[str, str], dict]:
    with path.open(newline="") as handle:
        return {(row["fly_id"], row["roi_id"]): row for row in csv.DictReader(handle)}


def _finite_median(values):
    values = [value for value in values if np.isfinite(value)]
    return float(np.median(values)) if values else None


def _compare_pair(model_path: Path, baseline_path: Path) -> dict:
    model, baseline = _read_scores(model_path), _read_scores(baseline_path)
    if set(model) != set(baseline):
        raise ValueError("Comparison ROI keys differ")
    by_fly: dict[str, list[float]] = {}
    all_deltas, responsive = [], []
    for key, row in model.items():
        if not row["r2"] or not baseline[key]["r2"]:
            continue
        delta = float(row["r2"]) - float(baseline[key]["r2"])
        by_fly.setdefault(key[0], []).append(delta)
        all_deltas.append(delta)
        if row["train_defined_responsive"] == "True":
            responsive.append(delta)
    per_fly = {fly: {"median_delta_r2": _finite_median(values),
                     "fraction_roi_improved": float(np.mean(np.asarray(values) > 0))}
               for fly, values in sorted(by_fly.items())}
    return {"all_roi_median_delta_r2": _finite_median(all_deltas),
            "responsive_median_delta_r2": _finite_median(responsive),
            "all_roi_fraction_improved": float(np.mean(np.asarray(all_deltas) > 0)),
            "fly_count_with_positive_median_delta": sum(value["median_delta_r2"] > 0
                                                        for value in per_fly.values()),
            "per_fly": per_fly}


def compare_cross_fold(root: Path) -> dict:
    """Compare saved ROI scores and kernels across two folds without writing.

    Inputs are Stage 10 model artifacts. Output is a fly-aware summary dict;
    no model fitting or experimental source mutation occurs here.
    """
    pairs = {
        "shared_strf_affine": "individual_ridge",
        "shared_plus_fly_deviation": "individual_ridge",
        "shared_factorized_basis": "individual_ridge",
        "shared_strf_equal_roi": "individual_ridge",
        "shared_strf_raw_units": "individual_ridge__raw_units",
        "shared_strf_validation_selected_response": "individual_ridge_validation_selected_response",
    }
    output = {"comparison_unit": "ROI within fly; fly is biological replicate",
              "test_status": "historical exploratory test, already used in earlier project stages",
              "folds": {}, "parameter_stability": {}}
    for fold in ("fold_a", "fold_b"):
        model_root = root / fold / "models"
        output["folds"][fold] = {name: _compare_pair(
            model_root / name / "roi_test_metrics.csv",
            model_root / baseline / "roi_test_metrics.csv") for name, baseline in pairs.items()}
    for name, key in (("shared_strf_affine", "shared_kernel"),
                      ("shared_factorized_basis", "basis")):
        paths = [root / fold / "models" / name / "model_parameters.npz" for fold in ("fold_a", "fold_b")]
        with np.load(paths[0]) as first, np.load(paths[1]) as second:
            a = first[key][0] if key == "basis" else first[key]
            b = second[key][0] if key == "basis" else second[key]
        cosine = float(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-12))
        output["parameter_stability"][name] = {"absolute_first_direction_cosine": abs(cosine),
            "sign_ambiguous_cosine": cosine,
            "note": "A broad shared training prefix makes these two fits correlated; this is descriptive, not independent replication."}
    return output


def write_cross_fold_comparison(root: Path) -> dict:
    """Persist the historical Phase 5 comparison at its existing path."""
    output = compare_cross_fold(root)
    path = root / "cross_fold_comparison.json"
    path.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    return output
