"""Exploratory RF repeatability and candidate-preprocessing diagnostics.

Uses stimulus [update,225] and payload ROI intensity [frame,ROI]. Previous
test-selected pixel metrics are descriptive only; Phase 5 selection is separate.
"""
from __future__ import annotations
import numpy as np
from ..features.lagged import lagged_design
from ..rf.null_tests import _shift_p_values
from ..preprocessing import candidate_response
from .diagnostics import _corr

def _rf_rows(aligned, pixel_metrics: dict | None) -> tuple[list[dict], list[dict]]:
    """Split the early 70% for two independent STA estimates; score the late 30%."""
    lags = 18
    eligible = aligned.update_index >= lags - 1
    indices = aligned.update_index[eligible]
    design = lagged_design(aligned.stimulus, indices, lags).astype(np.float64)
    y_raw = aligned.response[eligible]
    split = int(len(design) * .35)
    early_end = int(len(design) * .7)
    x1, x2, xt = design[:split], design[split:early_end], design[early_end:]
    x1 = x1 - x1.mean(axis=0)
    x2 = x2 - x2.mean(axis=0)
    xt = xt - design[:early_end].mean(axis=0)
    roi_rows = []
    candidate_rows = []
    pixel_by_label = {row["roi"]: row for row in (pixel_metrics or {}).get("roi_metrics", [])}
    for kind in ("raw", "causal_ema_residual_60s", "candidate_ema_dff_60s"):
        y = candidate_response(aligned.response, aligned.imaging_time_us, kind)[eligible].astype(np.float64)
        y1, y2, yt = y[:split], y[split:early_end], y[early_end:]
        k1 = x1.T @ (y1 - y1.mean(axis=0)) / len(x1)
        k2 = x2.T @ (y2 - y2.mean(axis=0)) / len(x2)
        agreement = _corr(k1, k2)
        prediction = xt @ k1
        test_r = _corr(yt, prediction)
        candidate_rows.append({"fly": aligned.session.fly, "run_id": aligned.session.run_id,
                               "candidate": kind, "median_split_half_kernel_r": float(np.median(agreement)),
                               "median_late_projection_r": float(np.median(test_r)),
                               "positive_late_projection_roi_count": int(np.sum(test_r > 0))})
        if kind != "raw":
            continue
        # Circularly shift the second early block's ROI trace against the
        # first-block RF projection. This preserves autocorrelation while
        # breaking the stimulus/response alignment; 30-frame near shifts are
        # excluded. The null is a projection test, not a full RF FDR test.
        split_null_p = _shift_p_values(y2, x2 @ k1, 30)
        for roi, label in enumerate(aligned.roi_labels):
            matrix = k1[:, roi].reshape(lags, 225)
            singular = np.linalg.svd(matrix, compute_uv=False)
            energy = float(singular[0] ** 2 / np.sum(singular ** 2)) if np.any(singular) else 0.0
            pixel = pixel_by_label.get(label, {})
            q = pixel.get("shift_null_q_all_rois")
            pixel_r = pixel.get("test_r")
            stable = bool(pixel.get("pixel_stable_train_validation"))
            if q is not None and q < .05 and pixel_r is not None and pixel_r > 0 and stable and agreement[roi] > 0 and split_null_p[roi] < .05:
                confidence = "HIGH_CONFIDENCE_RESPONSIVE"
            elif q is not None and q < .05 and pixel_r is not None and pixel_r > 0:
                confidence = "MODERATE_CONFIDENCE"
            elif agreement[roi] > 0 and test_r[roi] > 0:
                confidence = "LOW_CONFIDENCE"
            else:
                confidence = "NO_DETECTABLE_RF"
            center = int(np.argmax(np.sum(matrix * matrix, axis=0)))
            roi_rows.append({"fly": aligned.session.fly, "run_id": aligned.session.run_id,
                             "roi": label, "split_half_kernel_r": float(agreement[roi]),
                             "split_half_projection_shift_null_p": float(split_null_p[roi]),
                             "late_projection_r": float(test_r[roi]), "rank_one_energy_fraction": energy,
                             "train_rf_peak_row": center // 15, "train_rf_peak_col": center % 15,
                             "pixel_model_test_r": pixel_r, "pixel_model_shift_q": q,
                             "pixel_location_stable": stable, "rf_confidence": confidence})
    return roi_rows, candidate_rows
