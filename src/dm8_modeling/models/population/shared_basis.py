"""Shared low-rank spatiotemporal basis with ROI-specific mixing weights.

Training-only individual Ridge kernels are stacked across flies, SVD yields
candidate shared directions, and each [temporal bin,15x15] direction is
factorized to one temporal vector times one spatial map. ROI readouts use
only TRAIN for validation selection, then train+validation for final TEST.
Q=1..4 controls shared parameter count and is chosen by validation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...datasets.splits import TRAIN, VALIDATION
from ...evaluation.metrics import score_columns
from ..linear.ridge import RidgeSystem


@dataclass(frozen=True)
class BasisFit:
    name: str
    basis: np.ndarray  # [Q, feature], each reshapes to [bin,15,15]
    temporal_components: np.ndarray  # [Q, bin]
    spatial_components: np.ndarray  # [Q, 15, 15]
    heads: dict[str, np.ndarray]  # [Q,ROI]
    intercepts: dict[str, np.ndarray]  # [ROI]
    predictions: dict[str, np.ndarray]
    basis_count: int
    head_alpha: float
    validation_median_r2: float
    validation_candidates: tuple[dict, ...]


def _training_kernel_matrix(individuals, processed: dict, masks: dict[str, np.ndarray],
                            individual_alphas: dict[str, float]) -> np.ndarray:
    columns = []
    for item in individuals:
        mask = masks[item.fly_id]
        fit = RidgeSystem.from_arrays(item.features(mask), processed[item.fly_id].values[mask]).fit(
            individual_alphas[item.fly_id])
        coefficients = fit.coefficient.T
        norms = np.linalg.norm(coefficients, axis=1, keepdims=True)
        columns.append(coefficients / np.maximum(norms, 1e-12) / np.sqrt(len(item.roi_labels)))
    return np.concatenate(columns, axis=0)


def _factorized_basis(matrix: np.ndarray, bins: int, rank: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _, _, right = np.linalg.svd(matrix, full_matrices=False)
    basis, temporal, spatial = [], [], []
    for candidate in right[:rank]:
        u, singular, vh = np.linalg.svd(candidate.reshape(bins, 225), full_matrices=False)
        time = u[:, 0]
        space = vh[0]
        component = np.outer(time, space).reshape(-1)
        component /= np.linalg.norm(component)
        basis.append(component)
        temporal.append(time)
        spatial.append(space.reshape(15, 15))
    return np.asarray(basis), np.asarray(temporal), np.asarray(spatial)


def _fit_heads(individuals, processed: dict, masks: dict[str, np.ndarray],
               basis: np.ndarray, alpha: float) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    heads, intercepts = {}, {}
    for item in individuals:
        mask = masks[item.fly_id]
        x = item.features(mask).astype(np.float64) @ basis.T
        y = processed[item.fly_id].values[mask].astype(np.float64)
        mx, my = x.mean(axis=0), y.mean(axis=0)
        xc, yc = x - mx, y - my
        head = np.linalg.solve(xc.T @ xc / len(x) + alpha * np.eye(basis.shape[0]), xc.T @ yc / len(x))
        heads[item.fly_id] = head
        intercepts[item.fly_id] = my - mx @ head
    return heads, intercepts


def _predict(item, basis: np.ndarray, heads: dict, intercepts: dict) -> np.ndarray:
    return (item.X.astype(np.float64) @ basis.T) @ heads[item.fly_id] + intercepts[item.fly_id]


def fit_shared_basis(individuals, processed: dict, individual_ridge_fit,
                     ranks: tuple[int, ...], head_alphas: tuple[float, ...]) -> BasisFit:
    if not ranks or not head_alphas or min(ranks) < 1 or min(head_alphas) <= 0:
        raise ValueError("Positive ranks and head penalties required")
    individual_alphas = {fly: float(parameters["alpha"]) for fly, parameters in
                         individual_ridge_fit.parameters.items()}
    train_masks = {item.fly_id: item.split_label == TRAIN for item in individuals}
    matrix = _training_kernel_matrix(individuals, processed, train_masks, individual_alphas)
    bins = individuals[0].feature_definition.bins
    candidates = []
    cache = {}
    for rank in ranks:
        basis, temporal, spatial = _factorized_basis(matrix, bins, rank)
        cache[rank] = basis, temporal, spatial
        for alpha in head_alphas:
            heads, intercepts = _fit_heads(individuals, processed, train_masks, basis, alpha)
            scores = []
            for item in individuals:
                val = item.split_label == VALIDATION
                train_var = np.var(processed[item.fly_id].values[train_masks[item.fly_id]].astype(np.float64), axis=0)
                prediction = _predict(item, basis, heads, intercepts)[val]
                scores.extend(score_columns(processed[item.fly_id].values[val], prediction, train_var)["r2"].tolist())
            candidates.append({"rank": int(rank), "head_alpha": float(alpha),
                               "median_validation_r2": float(np.nanmedian(scores))})
    best = max(candidates, key=lambda row: row["median_validation_r2"])
    fit_masks = {item.fly_id: (item.split_label == TRAIN) | (item.split_label == VALIDATION)
                 for item in individuals}
    matrix = _training_kernel_matrix(individuals, processed, fit_masks, individual_alphas)
    basis, temporal, spatial = _factorized_basis(matrix, bins, best["rank"])
    heads, intercepts = _fit_heads(individuals, processed, fit_masks, basis, best["head_alpha"])
    predictions = {item.fly_id: _predict(item, basis, heads, intercepts) for item in individuals}
    return BasisFit("shared_factorized_basis", basis, temporal, spatial,
                    heads, intercepts, predictions, best["rank"], best["head_alpha"],
                    best["median_validation_r2"], tuple(candidates))
