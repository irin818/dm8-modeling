"""Partial pooling: shared STRF plus a penalized fly-specific deviation.

K_f = K_shared + Delta_f; y_fr = b_fr + g_fr X_f K_f. The shared core and
ROI readouts are learned across flies, whereas each Delta_f is fitted from
that fly's residual on TRAIN. Validation chooses one global fly penalty.
The model deliberately stops short of per-ROI kernel deviations in this
small-data first round.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...datasets.splits import TRAIN, VALIDATION
from ...evaluation.metrics import score_columns
from .shared_strf import SharedCore, SharedFit, fit_shared_core


@dataclass(frozen=True)
class HierarchicalFit:
    name: str
    shared_core: SharedCore
    fly_deviation: dict[str, np.ndarray]
    predictions: dict[str, np.ndarray]
    lambda_fly: float
    validation_median_r2: float
    validation_candidates: tuple[dict, ...]


def fit_fly_deviations(individuals, processed: dict, masks: dict[str, np.ndarray],
                       core: SharedCore, lambda_fly: float) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    if lambda_fly <= 0:
        raise ValueError("Positive fly-deviation penalty required")
    deltas, means = {}, {}
    for item in individuals:
        mask = masks[item.fly_id]
        x = item.features(mask).astype(np.float64)
        y = processed[item.fly_id].values[mask].astype(np.float64)
        x_mean = x.mean(axis=0)
        xc = x - x_mean
        residual = y - (x @ core.kernel)[:, None] * core.gains[item.fly_id] - core.biases[item.fly_id]
        gain = core.gains[item.fly_id]
        gram = xc.T @ xc / len(x) * float(np.mean(gain * gain))
        cross = xc.T @ (residual @ gain) / (len(x) * len(gain))
        deltas[item.fly_id] = np.linalg.solve(gram + lambda_fly * np.eye(x.shape[1]), cross)
        means[item.fly_id] = x_mean
    return deltas, means


def predict_with_deviations(individual, core: SharedCore, delta: np.ndarray, x_mean: np.ndarray) -> np.ndarray:
    x = individual.X.astype(np.float64)
    shared = core.predict(individual)
    return shared + ((x - x_mean) @ delta)[:, None] * core.gains[individual.fly_id]


def fit_hierarchical_strf(individuals, processed: dict, shared_fit: SharedFit,
                          penalties: tuple[float, ...], iterations: int = 5) -> HierarchicalFit:
    train_masks = {item.fly_id: item.split_label == TRAIN for item in individuals}
    training_core = fit_shared_core(individuals, processed, train_masks, shared_fit.core.alpha,
                                    iterations, shared_fit.core.loss_weighting)
    candidates = []
    for penalty in penalties:
        deltas, means = fit_fly_deviations(individuals, processed, train_masks, training_core, penalty)
        scores = []
        for item in individuals:
            val = item.split_label == VALIDATION
            prediction = predict_with_deviations(item, training_core, deltas[item.fly_id], means[item.fly_id])
            train_var = np.var(processed[item.fly_id].values[train_masks[item.fly_id]].astype(np.float64), axis=0)
            scores.extend(score_columns(processed[item.fly_id].values[val], prediction[val], train_var)["r2"].tolist())
        candidates.append({"lambda_fly": float(penalty), "median_validation_r2": float(np.nanmedian(scores))})
    best = max(candidates, key=lambda row: row["median_validation_r2"])
    fit_masks = {item.fly_id: (item.split_label == TRAIN) | (item.split_label == VALIDATION)
                 for item in individuals}
    deltas, means = fit_fly_deviations(individuals, processed, fit_masks, shared_fit.core, best["lambda_fly"])
    predictions = {item.fly_id: predict_with_deviations(item, shared_fit.core,
                    deltas[item.fly_id], means[item.fly_id]) for item in individuals}
    return HierarchicalFit("shared_plus_fly_deviation", shared_fit.core, deltas, predictions,
                           best["lambda_fly"], best["median_validation_r2"], tuple(candidates))
