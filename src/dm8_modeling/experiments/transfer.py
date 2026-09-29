"""Leave-one-fly-out biological transfer with a synchronized stimulus fold.

The held-out fly never contributes to shared-kernel fitting or alpha choice.
Zero-shot uses a fixed average readout from source flies; few-shot freezes the
kernel and fits only gain/bias from the first part of the held-out fly's TRAIN
interval. The target scaler uses its own TRAIN values solely to define units.
Five flies share one frozen stimulus, so ROI rows are not independent animals.
"""

from __future__ import annotations

import numpy as np

from ..datasets.splits import TRAIN, TEST
from ..models.population.shared_strf import fit_shared_strf
from ..evaluation.metrics import score_columns


def leave_one_fly_out(individuals, processed: dict, alphas: tuple[float, ...],
                      few_shot_fraction: float = .2, iterations: int = 5) -> list[dict]:
    if not 0 < few_shot_fraction <= 1:
        raise ValueError("Few-shot fraction must be in (0,1]")
    records = []
    for target in individuals:
        sources = [item for item in individuals if item.fly_id != target.fly_id]
        fit = fit_shared_strf(sources, processed, alphas, iterations=iterations)
        projection = target.X.astype(np.float64) @ fit.core.kernel
        source_gain = np.concatenate(list(fit.core.gains.values()))
        source_bias = np.concatenate(list(fit.core.biases.values()))
        zero_shot = projection[:, None] * float(np.median(source_gain)) + float(np.median(source_bias))
        zero_shot = np.repeat(zero_shot, len(target.roi_labels), axis=1)
        train_rows = np.flatnonzero(target.split_label == TRAIN)
        count = max(50, int(len(train_rows) * few_shot_fraction))
        few_rows = train_rows[:count]
        z = projection[few_rows]
        y = processed[target.fly_id].values[few_rows].astype(np.float64)
        centered_z = z - z.mean()
        denominator = float(centered_z @ centered_z)
        gain = (centered_z @ (y - y.mean(axis=0))) / max(denominator, 1e-12)
        bias = y.mean(axis=0) - gain * z.mean()
        adapted = projection[:, None] * gain + bias
        test = target.split_label == TEST
        actual = processed[target.fly_id].values[test]
        train_variance = np.var(processed[target.fly_id].values[target.split_label == TRAIN].astype(np.float64), axis=0)
        for mode, prediction in (("zero_shot", zero_shot), ("few_shot_readout", adapted)):
            scores = score_columns(actual, prediction[test], train_variance)
            for roi, label in enumerate(target.roi_labels):
                records.append({"heldout_fly": target.fly_id, "roi_id": label, "mode": mode,
                                "pearson_r": float(scores["pearson_r"][roi]),
                                "r2": float(scores["r2"][roi]),
                                "mse": float(scores["mse"][roi]),
                                "normalized_mse": float(scores["normalized_mse"][roi]),
                                "few_shot_train_frames": count if mode == "few_shot_readout" else 0,
                                "source_fly_count": len(sources), "selected_alpha": fit.core.alpha})
    return records
