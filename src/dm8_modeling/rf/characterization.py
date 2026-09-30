"""TRAIN-only descriptive RF estimation, reliability, and center alignment."""

from __future__ import annotations

import numpy as np

from .null_tests import _shift_p_values


def _correlation(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = left - left.mean(axis=0)
    right = right - right.mean(axis=0)
    denominator = np.linalg.norm(left, axis=0) * np.linalg.norm(right, axis=0)
    return np.divide(np.sum(left * right, axis=0), denominator,
                     out=np.zeros(left.shape[1]), where=denominator > 0)


def reverse_correlation(design: np.ndarray, response: np.ndarray) -> np.ndarray:
    """Centered stimulus-response covariance, [feature, ROI]."""
    if design.ndim != 2 or response.ndim != 2 or len(design) != len(response):
        raise ValueError("Expected matching [frame,feature] and [frame,ROI] arrays")
    if len(design) < 2 or not np.isfinite(design).all() or not np.isfinite(response).all():
        raise ValueError("RF input must have at least two finite frames")
    return (design - design.mean(axis=0)).T @ (response - response.mean(axis=0)) / len(design)


def fdr_q_values(p_values: np.ndarray) -> np.ndarray:
    """BH over one prespecified family; non-finite p-values get q=1."""
    p_values = np.asarray(p_values, dtype=float)
    if p_values.ndim != 1 or np.any((p_values[np.isfinite(p_values)] < 0) |
                                     (p_values[np.isfinite(p_values)] > 1)):
        raise ValueError("Expected one-dimensional probabilities")
    result = np.ones(len(p_values), dtype=float)
    valid = np.flatnonzero(np.isfinite(p_values))
    if not len(valid):
        return result
    order = valid[np.argsort(p_values[valid])]
    ranks = np.arange(1, len(order) + 1)
    adjusted = np.minimum.accumulate((p_values[order] * len(order) / ranks)[::-1])[::-1]
    result[order] = np.minimum(adjusted, 1)
    return result


def classify_rf(row: dict, config: dict) -> str:
    """Classify stimulus-response RF evidence, never biological identity."""
    if (row["valid_trace"] and row["shift_null_q_all_candidates_all_rois"] <= config["fdr_q_max"]
            and row["split_half_rf_r"] >= config["min_split_half_rf_r"]
            and row["train_projection_r"] >= config["min_train_projection_r"]
            and row["center_stable"]):
        return "RF_RELIABLE"
    if row["valid_trace"] and (row["train_projection_r"] > 0 or row["split_half_rf_r"] > 0):
        return "RF_WEAK"
    return "RF_UNRESOLVED"


def _gaussian_centers(profiles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit baseline + positive 1D Gaussian on a fixed, preregistered grid."""
    coordinates = np.arange(15, dtype=float)
    means = np.arange(0, 14.001, 0.25)
    widths = np.array([0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0])
    mu, sigma = np.meshgrid(means, widths, indexing="ij")
    template = np.exp(-0.5 * ((coordinates[None, :] - mu.ravel()[:, None]) /
                              sigma.ravel()[:, None]) ** 2)
    template -= template.mean(axis=1, keepdims=True)
    norm = np.sum(template * template, axis=1)
    centered = profiles - profiles.mean(axis=1, keepdims=True)
    score = centered @ template.T
    explained = np.maximum(score, 0) ** 2 / norm
    best = np.argmax(explained, axis=1)
    power = np.sum(centered * centered, axis=1)
    quality = np.divide(explained[np.arange(len(best)), best], power,
                        out=np.zeros(len(best)), where=power > 1e-12)
    center = mu.ravel()[best].astype(float)
    center[(power <= 1e-12) | (quality < 0.05)] = np.nan
    return center, quality


def rf_maps(kernel: np.ndarray, bins: int) -> dict[str, np.ndarray]:
    """Return sign-oriented spatial map, temporal profile and Li-style center.

    The dominant temporal bin supplies the spatial cross-sections. The
    maximum absolute pixel sets polarity; each row/column profile is fitted
    independently with an offset + positive 1D Gaussian.
    """
    if kernel.ndim != 2 or kernel.shape[0] != bins * 225:
        raise ValueError("Expected [bins*225,ROI] RF")
    n_roi = kernel.shape[1]
    # Li-style RF normalization is per ROI across the full spatiotemporal RF.
    # It changes units, not the center estimate from an offset Gaussian fit.
    centered = kernel - kernel.mean(axis=0)
    scale = np.std(centered, axis=0)
    normalized = np.divide(centered, scale, out=np.zeros_like(centered), where=scale > 1e-12)
    maps = normalized.reshape(bins, 15, 15, n_roi)
    energy = np.sum(maps * maps, axis=(1, 2))
    dominant = np.argmax(energy, axis=0)
    spatial = np.empty((15, 15, n_roi), dtype=float)
    temporal = np.empty((bins, n_roi), dtype=float)
    row_profile = np.empty((n_roi, 15), dtype=float)
    col_profile = np.empty((n_roi, 15), dtype=float)
    for roi in range(n_roi):
        image = maps[dominant[roi], :, :, roi]
        peak = np.unravel_index(np.argmax(np.abs(image)), image.shape)
        sign = 1.0 if image[peak] >= 0 else -1.0
        oriented = sign * image
        spatial[:, :, roi] = oriented
        row_profile[roi] = oriented[:, peak[1]]
        col_profile[roi] = oriented[peak[0], :]
        denominator = np.sum(image * image)
        temporal[:, roi] = (np.sum(maps[:, :, :, roi] * image[None], axis=(1, 2)) /
                            denominator if denominator > 0 else 0)
    row, row_quality = _gaussian_centers(row_profile)
    col, col_quality = _gaussian_centers(col_profile)
    centers = np.column_stack((row, col))
    # A fit-quality-derived sensitivity indicator, not a statistical CI.
    uncertainty = 1 - np.minimum(row_quality, col_quality)
    uncertainty[~np.isfinite(centers).all(axis=1)] = np.nan
    return {"normalized_kernel": normalized, "spatial": spatial,
            "temporal": temporal, "centers": centers,
            "center_fit_uncertainty_heuristic": uncertainty,
            "center_fit_quality": np.minimum(row_quality, col_quality),
            "dominant_bin": dominant}


def characterize_halves(
    first_x: np.ndarray, first_y: np.ndarray,
    second_x: np.ndarray, second_y: np.ndarray,
    bins: int, null_exclusion_frames: int,
) -> dict[str, np.ndarray]:
    """Estimate RF A/B and project RF A onto response B, all on TRAIN."""
    if first_x.shape[1] != second_x.shape[1] or first_y.shape[1] != second_y.shape[1]:
        raise ValueError("TRAIN halves must share feature and ROI axes")
    first = reverse_correlation(first_x, first_y)
    second = reverse_correlation(second_x, second_y)
    combined = reverse_correlation(np.vstack((first_x, second_x)),
                                   np.vstack((first_y, second_y)))
    projection = (second_x - first_x.mean(axis=0)) @ first
    projection_r = _correlation(second_y, projection)
    split_r = _correlation(first, second)
    invalid = ((np.std(first_y, axis=0) <= 1e-8) |
               (np.std(second_y, axis=0) <= 1e-8))
    p = _shift_p_values(second_y, projection, exclusion=null_exclusion_frames)
    p[invalid] = 1
    first_maps, second_maps, full_maps = (rf_maps(k, bins) for k in (first, second, combined))
    displacement = np.linalg.norm(first_maps["centers"] - second_maps["centers"], axis=1)
    return {"kernel_first": first, "kernel_second": second, "kernel_full": combined,
            "kernel_full_zscore": full_maps["normalized_kernel"],
            "spatial": full_maps["spatial"], "temporal": full_maps["temporal"],
            "center": full_maps["centers"], "center_first": first_maps["centers"],
            "center_second": second_maps["centers"],
            "center_fit_uncertainty_heuristic": full_maps["center_fit_uncertainty_heuristic"],
            "center_fit_quality": full_maps["center_fit_quality"],
            "dominant_bin": full_maps["dominant_bin"],
            "split_half_rf_r": split_r, "train_projection_r": projection_r,
            "shift_null_p": p, "center_displacement": displacement,
            "invalid_trace": invalid}


def align_kernels(kernels: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Integer, zero-padded translation to grid center (7,7), no wrapping."""
    if kernels.ndim != 4 or kernels.shape[1:3] != (15, 15) or centers.shape != (kernels.shape[3], 2):
        raise ValueError("Expected [bin,15,15,ROI] RF and [ROI,2] centers")
    result = np.zeros_like(kernels)
    for roi, (row, col) in enumerate(centers):
        if not np.isfinite((row, col)).all():
            continue
        dr, dc = 7 - int(np.rint(row)), 7 - int(np.rint(col))
        source_rows = slice(max(0, -dr), min(15, 15 - dr))
        source_cols = slice(max(0, -dc), min(15, 15 - dc))
        dest_rows = slice(max(0, dr), min(15, 15 + dr))
        dest_cols = slice(max(0, dc), min(15, 15 + dc))
        result[:, dest_rows, dest_cols, roi] = kernels[:, source_rows, source_cols, roi]
    return result


def pairwise_spatial_similarity(spatial: np.ndarray, groups: np.ndarray | None = None) -> dict[str, float | None]:
    """Mean within/cross-fly Pearson similarity between sign-oriented RFs."""
    if spatial.ndim != 3 or spatial.shape[:2] != (15, 15):
        raise ValueError("Expected [15,15,ROI] spatial maps")
    n = spatial.shape[2]
    if n < 2:
        return {"within_fly": None, "cross_fly": None, "all": None}
    flat = spatial.reshape(225, n).T.copy()
    flat -= flat.mean(axis=1, keepdims=True)
    norm = np.linalg.norm(flat, axis=1, keepdims=True)
    flat = np.divide(flat, norm, out=np.zeros_like(flat), where=norm > 0)
    matrix = flat @ flat.T
    pairs = np.triu_indices(n, 1)
    values = matrix[pairs]
    if groups is None:
        return {"within_fly": float(values.mean()), "cross_fly": None, "all": float(values.mean())}
    same = groups[pairs[0]] == groups[pairs[1]]
    return {"within_fly": float(values[same].mean()) if np.any(same) else None,
            "cross_fly": float(values[~same].mean()) if np.any(~same) else None,
            "all": float(values.mean())}
