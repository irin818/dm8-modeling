"""One shared causal STRF with one affine gain and bias per recorded ROI.

For fly f, ROI r, y_fr(t) = b_fr + g_fr X_f(t) K_shared. X has [frame,900]
shape for four past temporal bins on a 15x15 grid. Alternating weighted
Ridge updates fit K and ROI heads on TRAIN only; validation chooses alpha;
train+validation then refit for held-out TEST. Equal-fly weights prevent a fly
with more ROIs from dominating. Raw or train-standardized y is explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...datasets.splits import TRAIN, VALIDATION
from ...evaluation.metrics import score_columns


@dataclass(frozen=True)
class SharedCore:
    kernel: np.ndarray  # [feature], normalized direction
    gains: dict[str, np.ndarray]  # each [ROI]
    biases: dict[str, np.ndarray]  # each [ROI]
    alpha: float
    loss_weighting: str

    def predict(self, individual) -> np.ndarray:
        z = individual.X.astype(np.float64) @ self.kernel
        return z[:, None] * self.gains[individual.fly_id] + self.biases[individual.fly_id]


@dataclass(frozen=True)
class SharedFit:
    name: str
    core: SharedCore
    predictions: dict[str, np.ndarray]
    validation_median_r2: float
    validation_candidates: tuple[dict, ...]


def fit_shared_core(individuals, processed: dict, masks: dict[str, np.ndarray],
                    alpha: float, iterations: int = 5, loss_weighting: str = "equal_fly") -> SharedCore:
    """Alternate K direction and per-ROI heads without using held-out rows."""
    if alpha <= 0 or iterations < 1 or loss_weighting not in {"equal_fly", "equal_roi"}:
        raise ValueError("Invalid shared STRF regularization, iterations or weighting")
    statistics = {}
    cross_columns = []
    total_rois = sum(len(item.roi_labels) for item in individuals)
    for item in individuals:
        mask = masks[item.fly_id]
        x = item.features(mask).astype(np.float64)
        y = processed[item.fly_id].values[mask].astype(np.float64)
        mx, my = x.mean(axis=0), y.mean(axis=0)
        xc, yc = x - mx, y - my
        gram = xc.T @ xc / len(x)
        cross = xc.T @ yc / len(x)
        weight = 1 / (len(individuals) * y.shape[1]) if loss_weighting == "equal_fly" else 1 / total_rois
        statistics[item.fly_id] = (mx, my, gram, cross, weight)
        norms = np.linalg.norm(cross, axis=0)
        cross_columns.append((cross / np.maximum(norms, 1e-12)).T)
    matrix = np.concatenate(cross_columns, axis=0)
    _, _, right = np.linalg.svd(matrix, full_matrices=False)
    kernel = right[0].copy()
    for _ in range(iterations):
        weighted_gram = np.zeros((len(kernel), len(kernel)), dtype=np.float64)
        weighted_cross = np.zeros(len(kernel), dtype=np.float64)
        for item in individuals:
            _, _, gram, cross, weight = statistics[item.fly_id]
            variance = float(kernel @ gram @ kernel)
            gains = (kernel @ cross) / max(variance, 1e-12)
            weighted_gram += weight * float(gains @ gains) * gram
            weighted_cross += weight * (cross @ gains)
        updated = np.linalg.solve(weighted_gram + alpha * np.eye(len(kernel)), weighted_cross)
        norm = np.linalg.norm(updated)
        if norm < 1e-12:
            raise ValueError("Shared STRF collapsed to a zero direction")
        kernel = updated / norm
    gains_by_fly, biases_by_fly = {}, {}
    for item in individuals:
        mx, my, gram, cross, _ = statistics[item.fly_id]
        variance = float(kernel @ gram @ kernel)
        gain = (kernel @ cross) / max(variance, 1e-12)
        gains_by_fly[item.fly_id] = gain
        biases_by_fly[item.fly_id] = my - float(mx @ kernel) * gain
    return SharedCore(kernel, gains_by_fly, biases_by_fly, alpha, loss_weighting)


def fit_shared_strf(individuals, processed: dict, alphas: tuple[float, ...],
                    iterations: int = 5, loss_weighting: str = "equal_fly") -> SharedFit:
    if not alphas:
        raise ValueError("At least one shared alpha is required")
    train_masks = {item.fly_id: item.split_label == TRAIN for item in individuals}
    candidates = []
    for alpha in alphas:
        core = fit_shared_core(individuals, processed, train_masks, alpha, iterations, loss_weighting)
        roi_scores = []
        for item in individuals:
            val = item.split_label == VALIDATION
            train_y = processed[item.fly_id].values[train_masks[item.fly_id]]
            train_var = np.var(train_y.astype(np.float64), axis=0)
            predicted = core.predict(item)[val]
            roi_scores.extend(score_columns(processed[item.fly_id].values[val], predicted,
                                             train_var)["r2"].tolist())
        median = float(np.nanmedian(roi_scores))
        candidates.append({"alpha": float(alpha), "median_validation_r2": median})
    best = max(candidates, key=lambda row: row["median_validation_r2"])
    fit_masks = {item.fly_id: (item.split_label == TRAIN) | (item.split_label == VALIDATION)
                 for item in individuals}
    final = fit_shared_core(individuals, processed, fit_masks, best["alpha"], iterations, loss_weighting)
    predictions = {item.fly_id: final.predict(item) for item in individuals}
    return SharedFit("shared_strf_affine", final, predictions,
                     best["median_validation_r2"], tuple(candidates))
