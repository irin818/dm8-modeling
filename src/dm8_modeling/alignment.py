"""Gaussian RF centers and missing-support translations; no circular wrapping."""

import numpy as np
from scipy.ndimage import shift
from .rf import rf_zscore


def fit_axis_centers(profiles: np.ndarray, config: dict) -> np.ndarray:
    """Fit offset+positive Gaussian [ROI,15] profiles on a fixed center/width grid."""
    low, high, step = config["center_fit_mean_grid_px"]
    means = np.arange(low, high + step/2, step)
    mu, sigma = np.meshgrid(means, np.asarray(config["center_fit_widths_px"]), indexing="ij")
    coordinates = np.arange(profiles.shape[1], dtype=float)
    templates = np.exp(-.5 * ((coordinates[None, :]-mu.ravel()[:, None])/sigma.ravel()[:, None])**2)
    templates -= templates.mean(axis=1, keepdims=True)
    norm = np.sum(templates*templates, axis=1)
    centered = profiles-profiles.mean(axis=1, keepdims=True)
    score = centered @ templates.T
    explained = np.maximum(score, 0)**2/norm
    best = np.argmax(explained, axis=1)
    power = np.sum(centered*centered, axis=1)
    quality = np.divide(explained[np.arange(len(best)), best], power,
                        out=np.zeros(len(best)), where=power > 1e-12)
    centers = mu.ravel()[best].astype(float)
    centers[(power <= 1e-12) | (quality < config["center_fit_quality_min"])] = np.nan
    return centers


def gaussian_axis_centers(images: np.ndarray, config: dict) -> np.ndarray:
    """Locate signed [15,15,ROI] RFs from max-abs-pixel row/column Gaussian fits."""
    n_roi = images.shape[2]
    rows, cols = np.empty((n_roi, images.shape[0])), np.empty((n_roi, images.shape[1]))
    for roi in range(n_roi):
        image = images[:, :, roi]
        peak = np.unravel_index(np.argmax(np.abs(image)), image.shape)
        oriented = image * (1 if image[peak] >= 0 else -1)
        rows[roi] = oriented[:, peak[1]]
        cols[roi] = oriented[peak[0], :]
    return np.column_stack((fit_axis_centers(rows, config), fit_axis_centers(cols, config)))


def estimate_centers(spatial: np.ndarray, config: dict) -> np.ndarray:
    """Return primary [ROI,row/col] centers; normalize the extracted spatial slice."""
    if spatial.ndim != 3 or spatial.shape[:2] != (config["grid_size"],)*2 or not np.isfinite(spatial).all():
        raise ValueError("Expected finite [15,15,ROI] spatial RF")
    normalized = rf_zscore(spatial.reshape(-1, spatial.shape[2])).reshape(spatial.shape)
    return gaussian_axis_centers(normalized, config)


def subpixel_align(images: np.ndarray, centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Bilinear [15,15,ROI] translation with valid weights and NaN outside support."""
    if images.ndim != 3 or centers.shape != (images.shape[2], 2):
        raise ValueError("Expected [row,col,ROI] maps and [ROI,2] centers")
    out = np.full(images.shape, np.nan, dtype=float)
    target = (np.array(images.shape[:2])-1)/2
    for roi, center in enumerate(centers):
        if not np.isfinite(center).all():
            continue
        valid = np.isfinite(images[:, :, roi]).astype(float)
        displacement = target-center
        numerator = shift(np.nan_to_num(images[:, :, roi]), displacement, order=1, mode="constant", cval=0)
        support = shift(valid, displacement, order=1, mode="constant", cval=0)
        out[:, :, roi] = np.divide(numerator, support, out=np.full(images.shape[:2], np.nan), where=support > 1e-8)
    return out, np.isfinite(out)


def temporal_reference_centers(raw_kernel: np.ndarray, config: dict) -> np.ndarray:
    """Fixed full-record temporal diagnostic centers; 4×10 reference, not main RF."""
    lags, rows, cols, n_roi = raw_kernel.shape
    coarse = raw_kernel.reshape(lags//10, 10, rows, cols, n_roi).mean(axis=1)
    # Preserve the frozen full-STRF normalization convention for peak positioning.
    normalized = rf_zscore(rf_zscore(coarse.reshape(-1, n_roi))).reshape(coarse.shape)
    energy = np.sum(normalized*normalized, axis=(1,2))
    dominant = np.argmax(energy, axis=0)
    images = np.stack([normalized[dominant[i], :, :, i] for i in range(n_roi)], axis=2)
    return gaussian_axis_centers(images, config)


def align_temporal_reference(kernel: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Rounded NaN translation [lag,15,15,ROI] for the frozen full-record diagnostic."""
    aligned = np.full(kernel.shape, np.nan, dtype=float)
    size = kernel.shape[1]
    for roi, (row, col) in enumerate(centers):
        if not np.isfinite((row, col)).all():
            continue
        dr, dc = size//2-int(np.rint(row)), size//2-int(np.rint(col))
        source_rows, source_cols = slice(max(0,-dr),min(size,size-dr)), slice(max(0,-dc),min(size,size-dc))
        dest_rows, dest_cols = slice(max(0,dr),min(size,size+dr)), slice(max(0,dc),min(size,size+dc))
        aligned[:, dest_rows, dest_cols, roi] = kernel[:, source_rows, source_cols, roi]
    return aligned
