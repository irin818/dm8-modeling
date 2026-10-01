"""Native causal stimulus history and descriptive signed receptive fields."""

import numpy as np
from .preprocessing import relative_response


def native_design(stimulus: np.ndarray, updates: np.ndarray, lags: int) -> np.ndarray:
    """Return [frame,lag*pixel] past stimulus; lag0=current, no future columns."""
    if stimulus.ndim != 2 or updates.ndim != 1 or lags < 1 or not len(updates):
        raise ValueError("Invalid stimulus, indices or lag count")
    if updates.min() < lags - 1 or updates.max() >= len(stimulus):
        raise ValueError("Every frame needs complete saved causal stimulus history")
    out = np.empty((len(updates), lags * stimulus.shape[1]), dtype=np.float32)
    for lag in range(lags):
        out[:, lag*stimulus.shape[1]:(lag+1)*stimulus.shape[1]] = stimulus[updates-lag]
    return out


def reverse_correlation(design: np.ndarray, response: np.ndarray) -> np.ndarray:
    """Covariance [lag*pixel,ROI]; negative means ON associates with lower fluorescence."""
    if (design.ndim != 2 or response.ndim != 2 or len(design) != len(response)
            or len(design) < 2 or not np.isfinite(design).all() or not np.isfinite(response).all()):
        raise ValueError("Expected matching finite [frame,feature] and [frame,ROI]")
    return (design-design.mean(axis=0)).T @ (response-response.mean(axis=0)) / len(design)


def rf_zscore(kernel: np.ndarray) -> np.ndarray:
    """Normalize [coefficient,ROI] over each entire STRF; Li exact axis unspecified."""
    if kernel.ndim != 2 or not np.isfinite(kernel).all():
        raise ValueError("Expected finite [coefficient,ROI] RF")
    centered = kernel-kernel.mean(axis=0)
    scale = centered.std(axis=0)
    return np.divide(centered, scale, out=np.zeros_like(centered), where=scale > 1e-12)


def estimate_strf(recording, config: dict, *, trim: bool, shift: int = 0) -> dict:
    """Reprocess one recording, returning raw and zscored [40,15,15,ROI] RFs."""
    raw = np.roll(recording.response, shift, axis=0) if shift else recording.response
    response, margin = relative_response(raw, recording.frame_us, config)
    updates = recording.update_index
    eligible = (updates >= config["native_lags"]-1) & (updates < len(recording.stimulus))
    if trim:
        eligible[:margin] = False
        eligible[-margin:] = False
    valid = response[eligible].std(axis=0) > config["minimum_response_std"]
    if not valid.any():
        raise ValueError("No usable relative-response ROI")
    design = native_design(recording.stimulus, updates[eligible], config["native_lags"])
    raw_kernel = reverse_correlation(design, response[eligible][:, valid])
    shape = (config["native_lags"], config["grid_size"], config["grid_size"], -1)
    return {"raw_kernel": raw_kernel.reshape(shape), "kernel": rf_zscore(raw_kernel).reshape(shape),
            "frames": int(eligible.sum()), "roi_indices": recording.roi_indices[valid], "margin": margin}


def global_energy_lag(estimates: list[dict]) -> int:
    """Choose one global lag by equal-fly total RF energy; never by surround sign."""
    energy = np.mean([np.mean(np.sum(item["kernel"]**2, axis=(1,2)), axis=1)
                      for item in estimates], axis=0)
    return int(np.argmax(energy))


def zone_means(image: np.ndarray, config: dict) -> tuple[float, float]:
    """Signed center≤1.5px and surround3–6px means, finite pixels only."""
    rows, cols = np.mgrid[:image.shape[0], :image.shape[1]]
    radius = np.hypot(rows-image.shape[0]//2, cols-image.shape[1]//2)
    center = image[(radius <= config["center_zone_radius_px"]) & np.isfinite(image)]
    surround = image[(radius >= config["surround_zone_inner_px"])
        & (radius <= config["surround_zone_outer_px"]) & np.isfinite(image)]
    return float(center.mean()) if len(center) else np.nan, float(surround.mean()) if len(surround) else np.nan
