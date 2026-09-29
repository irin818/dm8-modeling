"""Held-out scores for each ROI, preserving fly-level aggregation.

Input arrays are [test imaging frame,ROI]. Pearson r and R² use only the test
block; normalized MSE divides by each ROI's training variance. Constant
targets yield null r/R² rather than invented perfect scores.
"""

from __future__ import annotations

import numpy as np


def score_columns(actual: np.ndarray, predicted: np.ndarray, train_variance: np.ndarray) -> dict[str, np.ndarray]:
    if actual.shape != predicted.shape or actual.ndim != 2 or train_variance.shape != (actual.shape[1],):
        raise ValueError("Expected matching [frame,ROI] targets/predictions and training variances")
    a = actual.astype(np.float64)
    p = predicted.astype(np.float64)
    ac, pc = a - a.mean(axis=0), p - p.mean(axis=0)
    numerator = np.sum(ac * pc, axis=0)
    denominator = np.sqrt(np.sum(ac * ac, axis=0) * np.sum(pc * pc, axis=0))
    pearson = np.divide(numerator, denominator, out=np.full(a.shape[1], np.nan), where=denominator > 0)
    mse = np.mean((a - p) ** 2, axis=0)
    test_variance = np.mean(ac * ac, axis=0)
    r2 = 1 - np.divide(mse, test_variance, out=np.full(a.shape[1], np.nan), where=test_variance > 0)
    normalized_mse = np.divide(mse, train_variance, out=np.full(a.shape[1], np.nan), where=train_variance > 0)
    return {"pearson_r": pearson, "r2": r2, "mse": mse, "normalized_mse": normalized_mse}


def summarize_roi_records(records: list[dict], baseline: dict[tuple[str, str], float] | None = None) -> dict:
    def finite(values):
        return np.asarray([value for value in values if value is not None and np.isfinite(value)], dtype=np.float64)
    r2 = finite([row["r2"] for row in records])
    subset = finite([row["r2"] for row in records if row["train_defined_responsive"]])
    summaries = {}
    for fly in sorted({row["fly_id"] for row in records}):
        rows = [row for row in records if row["fly_id"] == fly]
        values = finite([row["r2"] for row in rows])
        summaries[fly] = {"roi_count": len(rows), "median_r2": float(np.median(values)) if len(values) else None,
                          "mean_r2": float(np.mean(values)) if len(values) else None,
                          "positive_r2_fraction": float(np.mean(values > 0)) if len(values) else None,
                          "train_defined_responsive_count": sum(row["train_defined_responsive"] for row in rows)}
    improvements = []
    if baseline is not None:
        improvements = [row["r2"] - baseline[(row["fly_id"], row["roi_id"])] for row in records
                        if row["r2"] is not None and (row["fly_id"], row["roi_id"]) in baseline and
                        baseline[(row["fly_id"], row["roi_id"])] is not None]
    return {"roi_count": len(records), "all_roi_median_r2": float(np.median(r2)) if len(r2) else None,
            "all_roi_mean_r2": float(np.mean(r2)) if len(r2) else None,
            "all_roi_positive_r2_fraction": float(np.mean(r2 > 0)) if len(r2) else None,
            "train_defined_responsive_median_r2": float(np.median(subset)) if len(subset) else None,
            "train_defined_responsive_roi_count": len(subset),
            "fraction_improved_vs_individual": float(np.mean(np.asarray(improvements) > 0)) if improvements else None,
            "median_delta_r2_vs_individual": float(np.median(improvements)) if improvements else None,
            "per_fly": summaries}
