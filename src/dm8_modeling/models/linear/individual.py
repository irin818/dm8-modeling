"""Independent ROI baselines on exactly the same global stimulus folds.

Each fly keeps separate X [frame, 4*225] and y [frame,ROI]. Pixel selects one
spatial location on TRAIN, then fits its temporal-bin slopes; Ridge fits all
225 positions. Validation selects regularization, then train+validation are
refitted before a later TEST score. No other fly's response is used.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...datasets.splits import TRAIN, VALIDATION
from ...evaluation.metrics import score_columns
from .ridge import RidgeSystem


@dataclass(frozen=True)
class IndividualFit:
    name: str
    predictions: dict[str, np.ndarray]  # full eligible frame x ROI
    parameters: dict[str, dict[str, np.ndarray | float]]
    validation_median_r2: dict[str, float]


def _median_r2(actual: np.ndarray, predicted: np.ndarray, train_var: np.ndarray) -> float:
    values = score_columns(actual, predicted, train_var)["r2"]
    return float(np.nanmedian(values)) if np.any(np.isfinite(values)) else -np.inf


def fit_individual_ridge(individuals, processed: dict, alphas: tuple[float, ...]) -> IndividualFit:
    if not alphas or any(alpha <= 0 for alpha in alphas):
        raise ValueError("Positive ridge alphas required")
    predictions, parameters, validation = {}, {}, {}
    for item in individuals:
        y = processed[item.fly_id].values
        train = item.split_label == TRAIN
        val = item.split_label == VALIDATION
        x_train, x_val = item.features(train), item.features(val)
        train_var = np.var(y[train].astype(np.float64), axis=0)
        system = RidgeSystem.from_arrays(x_train, y[train])
        scores = [(_median_r2(y[val], system.fit(alpha).predict(x_val), train_var), alpha)
                  for alpha in alphas]
        _, alpha = max(scores, key=lambda pair: pair[0])
        fit_mask = train | val
        final = RidgeSystem.from_arrays(item.features(fit_mask), y[fit_mask]).fit(alpha)
        predictions[item.fly_id] = final.predict(item.X)
        parameters[item.fly_id] = {"coefficient": final.coefficient, "intercept": final.intercept,
                                   "alpha": float(alpha)}
        validation[item.fly_id] = max(score for score, _ in scores)
    return IndividualFit("individual_ridge", predictions, parameters, validation)


def _pixel_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    mx, my = x.mean(axis=0), float(y.mean())
    xc = x.astype(np.float64) - mx
    yc = y.astype(np.float64) - my
    beta = np.linalg.solve(xc.T @ xc / len(x) + alpha * np.eye(x.shape[1]), xc.T @ yc / len(x))
    return beta, my - float(mx @ beta)


def fit_individual_pixel(individuals, processed: dict, alphas: tuple[float, ...]) -> IndividualFit:
    """The same 40-update history and temporal bins as Phase 5 Ridge."""
    predictions, parameters, validation = {}, {}, {}
    for item in individuals:
        y = processed[item.fly_id].values
        train = item.split_label == TRAIN
        val = item.split_label == VALIDATION
        fit_mask = train | val
        x_train = item.features(train).astype(np.float64)
        centered_x = x_train - x_train.mean(axis=0)
        centered_y = y[train].astype(np.float64) - y[train].mean(axis=0)
        bins = item.feature_definition.bins
        pixels = 225
        reverse = (centered_x.T @ centered_y).reshape(bins, pixels, -1)
        selected = np.argmax(np.sum(reverse * reverse, axis=0), axis=0)
        whole_x = item.X.astype(np.float64)
        prediction = np.empty_like(y, dtype=np.float64)
        coefficients = np.empty((len(selected), bins), dtype=np.float64)
        intercepts = np.empty(len(selected), dtype=np.float64)
        chosen_alpha = np.empty(len(selected), dtype=np.float64)
        val_scores = []
        train_var = np.var(y[train].astype(np.float64), axis=0)
        for roi, pixel in enumerate(selected):
            columns = np.arange(bins) * pixels + pixel
            x = whole_x[:, columns]
            candidates = []
            for alpha in alphas:
                beta, intercept = _pixel_fit(x[train], y[train, roi], alpha)
                score = _median_r2(y[val, roi, None],
                                   (x[val] @ beta + intercept)[:, None], train_var[roi, None])
                candidates.append((score, alpha))
            best_score, alpha = max(candidates, key=lambda pair: pair[0])
            beta, intercept = _pixel_fit(x[fit_mask], y[fit_mask, roi], alpha)
            prediction[:, roi] = x @ beta + intercept
            coefficients[roi], intercepts[roi], chosen_alpha[roi] = beta, intercept, alpha
            val_scores.append(best_score)
        predictions[item.fly_id] = prediction
        parameters[item.fly_id] = {"selected_pixels": selected, "coefficient": coefficients,
                                   "intercept": intercepts, "alpha_by_roi": chosen_alpha}
        validation[item.fly_id] = float(np.median(val_scores))
    return IndividualFit("individual_pixel", predictions, parameters, validation)
