"""Frozen Phase 6.5 RF method comparisons; descriptive, not predictive."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import shift as image_shift
from scipy.optimize import least_squares

from .characterization import reverse_correlation, rf_maps
from .population import energy_centers, shift_to_center, valid_mean, zone_means


def native_design(stimulus: np.ndarray, updates: np.ndarray, lags: int = 40) -> np.ndarray:
    """Causal columns [lag0 pixels, lag1 pixels, ...], with no future update."""
    if stimulus.ndim != 2 or updates.ndim != 1 or lags < 1 or not len(updates):
        raise ValueError("Expected stimulus [update,pixel], update indices and positive lags")
    if updates.min() < lags - 1 or updates.max() >= len(stimulus):
        raise ValueError("Every response must have complete past stimulus history")
    out = np.empty((len(updates), lags * stimulus.shape[1]), dtype=np.float32)
    for lag in range(lags):
        out[:, lag * stimulus.shape[1]:(lag + 1) * stimulus.shape[1]] = stimulus[updates - lag]
    return out


def rf_zscore(kernel: np.ndarray) -> np.ndarray:
    """One mean and SD across *all* temporal/spatial RF coefficients per ROI."""
    if kernel.ndim != 2 or not np.isfinite(kernel).all():
        raise ValueError("Expected finite [coefficient,ROI] RF")
    centered = kernel - kernel.mean(axis=0)
    scale = centered.std(axis=0)
    return np.divide(centered, scale, out=np.zeros_like(centered), where=scale > 1e-12)


def native_rf(design: np.ndarray, response: np.ndarray) -> np.ndarray:
    """Raw relative-response covariance, then individual full-STRF zscore."""
    return rf_zscore(reverse_correlation(design, response))


def coarse_from_native(kernel: np.ndarray, updates_per_bin: int = 10) -> np.ndarray:
    if kernel.ndim != 4 or kernel.shape[0] % updates_per_bin:
        raise ValueError("Expected [lag,row,col,ROI] divisible into temporal bins")
    return kernel.reshape(kernel.shape[0] // updates_per_bin, updates_per_bin, *kernel.shape[1:]).mean(axis=1)


def centers_from_spatial(spatial: np.ndarray) -> np.ndarray:
    """Existing signed axis-Gaussian method applied to the chosen spatial RF."""
    if spatial.ndim != 3 or spatial.shape[:2] != (15, 15):
        raise ValueError("Expected [15,15,ROI] spatial maps")
    return rf_maps(spatial.reshape(225, -1), 1)["centers"]


def align_spatial(maps: np.ndarray, centers: np.ndarray, method: str) -> tuple[np.ndarray, np.ndarray]:
    """Translate maps to (7,7), preserving missing outside-field support."""
    if method == "integer":
        return shift_to_center(maps, centers)
    if method != "bilinear" or maps.ndim != 3 or maps.shape[:2] != (15, 15):
        raise ValueError("Use integer or bilinear alignment for 15x15 maps")
    out = np.full(maps.shape, np.nan, dtype=float)
    for roi, (row, col) in enumerate(centers):
        if not np.isfinite((row, col)).all():
            continue
        finite = np.isfinite(maps[:, :, roi]).astype(float)
        shift = (7 - row, 7 - col)
        numerator = image_shift(np.nan_to_num(maps[:, :, roi]), shift, order=1, mode="constant", cval=0)
        support = image_shift(finite, shift, order=1, mode="constant", cval=0)
        out[:, :, roi] = np.divide(numerator, support, out=np.full((15, 15), np.nan), where=support > 1e-8)
    return out, np.isfinite(out)


def aggregate(maps_by_fly: list[np.ndarray], mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return population mean, ROI support and fly support per aligned pixel."""
    if not maps_by_fly or any(m.ndim != 3 or m.shape[:2] != (15, 15) for m in maps_by_fly):
        raise ValueError("Expected aligned [15,15,ROI] maps for each fly")
    fly_maps = np.stack([valid_mean(m, 2)[0] for m in maps_by_fly], axis=2)
    roi_support = np.sum([np.isfinite(m).sum(axis=2) for m in maps_by_fly], axis=0)
    fly_support = np.isfinite(fly_maps).sum(axis=2)
    if mode == "fly_equal":
        mean = valid_mean(fly_maps, 2)[0]
    elif mode == "roi_equal":
        mean = valid_mean(np.concatenate(maps_by_fly, axis=2), 2)[0]
    else:
        raise ValueError("Expected fly_equal or roi_equal")
    return mean, roi_support, fly_support


def zone_values(image: np.ndarray, config: dict) -> tuple[float, float]:
    return zone_means(image, config["center_zone_radius_px"],
                      config["surround_zone_inner_px"], config["surround_zone_outer_px"])


def li_relative_dog(x: np.ndarray, y: np.ndarray, center_widths: tuple[float, float],
                    surround_widths: tuple[float, float], relative_max: float) -> dict:
    """Fit b + a*(Gcenter - Arel*Gsurround), a<=0; widths stay in px."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if x.shape != y.shape or len(x) < 7 or not np.isfinite(y).all():
        raise ValueError("Expected finite 1D projected RF")
    def prediction(p):
        b, a, sc, ss, relative = p
        return b + a * (np.exp(-x*x/(2*sc*sc)) - relative*np.exp(-x*x/(2*ss*ss)))
    lo = [-np.inf, -np.inf, center_widths[0], surround_widths[0], 0]
    hi = [np.inf, 0, center_widths[1], surround_widths[1], relative_max]
    seed = [float(y.mean()), min(float(y.min()-y.mean()), -1e-8), 1.5, 5., .25]
    fit = least_squares(lambda p: prediction(p)-y, np.clip(seed, np.array(lo)+1e-9, np.array(hi)-1e-9),
                        bounds=(lo, hi), max_nfev=2000)
    b, a, sc, ss, relative = fit.x
    sse = float(np.sum((prediction(fit.x)-y)**2))
    total = float(np.sum((y-y.mean())**2))
    return {"baseline": b, "center_amplitude": a, "center_sigma_px": sc,
            "surround_sigma_px": ss, "relative_surround_amplitude": relative,
            "surround_amplitude": -a*relative, "sse": sse,
            "r2": 1-sse/total if total > 0 else np.nan,
            "surround_at_bound": bool(relative < 1e-4 or ss > surround_widths[1]-1e-4)}


def raw_center_edge_distance(centers: np.ndarray) -> np.ndarray:
    return np.minimum.reduce((centers[:, 0], centers[:, 1], 14-centers[:, 0], 14-centers[:, 1]))
