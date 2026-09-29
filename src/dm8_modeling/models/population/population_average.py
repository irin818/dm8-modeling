"""One linear filter predicts each fly's training-defined population average.

Population targets are averages of standardized ROI traces, not a sixth fly
or independent stimulus sequence. The shared filter is trained on per-fly
average observations with equal fly weighting and scored per fly on TEST.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...datasets.splits import TRAIN, VALIDATION
from ...evaluation.metrics import score_columns
from ..linear.ridge import RidgeFit, RidgeSystem


@dataclass(frozen=True)
class PopulationFit:
    name: str
    ridge: RidgeFit
    predictions: dict[str, np.ndarray]  # [imaging frame] per fly
    validation_median_r2: float
    validation_candidates: tuple[dict, ...]


def fit_population_average(individuals, populations: dict, alphas: tuple[float, ...]) -> PopulationFit:
    if not alphas:
        raise ValueError("Population Ridge alphas required")
    # Equalize fly contribution through equal per-fly training row counts.
    train_count = min(int(np.sum(item.split_label == TRAIN)) for item in individuals)
    val_count = min(int(np.sum(item.split_label == VALIDATION)) for item in individuals)
    train_rows = {item.fly_id: np.flatnonzero(item.split_label == TRAIN)[:train_count] for item in individuals}
    val_rows = {item.fly_id: np.flatnonzero(item.split_label == VALIDATION)[:val_count] for item in individuals}
    x_train = np.concatenate([item.features(train_rows[item.fly_id]) for item in individuals])
    y_train = np.concatenate([populations[item.fly_id].response[train_rows[item.fly_id], None]
                              for item in individuals])
    system = RidgeSystem.from_arrays(x_train, y_train)
    candidates = []
    for alpha in alphas:
        fit = system.fit(alpha)
        scores = []
        for item in individuals:
            rows = val_rows[item.fly_id]
            target = populations[item.fly_id].response[rows, None]
            train_var = np.var(populations[item.fly_id].response[train_rows[item.fly_id]])
            score = score_columns(target, fit.predict(item.features(rows)), np.asarray([train_var]))["r2"][0]
            scores.append(score)
        candidates.append({"alpha": float(alpha), "median_validation_r2": float(np.nanmedian(scores))})
    best = max(candidates, key=lambda row: row["median_validation_r2"])
    fit_rows = {item.fly_id: np.flatnonzero((item.split_label == TRAIN) | (item.split_label == VALIDATION))
                for item in individuals}
    count = min(len(rows) for rows in fit_rows.values())
    x_fit = np.concatenate([item.features(fit_rows[item.fly_id][:count]) for item in individuals])
    y_fit = np.concatenate([populations[item.fly_id].response[fit_rows[item.fly_id][:count], None]
                            for item in individuals])
    final = RidgeSystem.from_arrays(x_fit, y_fit).fit(best["alpha"])
    predictions = {item.fly_id: final.predict(item.X)[:, 0] for item in individuals}
    return PopulationFit("population_average_ridge", final, predictions,
                         best["median_validation_r2"], tuple(candidates))
