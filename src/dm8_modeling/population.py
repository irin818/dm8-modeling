"""Equal-ROI within animal, equal-fly across animals, with finite support counts."""

import numpy as np
from .alignment import estimate_centers, subpixel_align, temporal_reference_centers, align_temporal_reference


def valid_mean(values: np.ndarray, axis: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean only finite contributors; return mean and count, never substitute zero."""
    valid = np.isfinite(values)
    count = valid.sum(axis=axis)
    total = np.where(valid, values, 0).sum(axis=axis)
    return np.divide(total, count, out=np.full_like(total, np.nan, dtype=float), where=count > 0), count


def fly_spatial(estimate: dict, lag: int, config: dict) -> dict:
    """Extract one global-lag RF, align ROIs, return [15,15] fly mean and support."""
    spatial = estimate["kernel"][lag]
    centers = estimate_centers(spatial, config)
    aligned, _ = subpixel_align(spatial, centers)
    image, count = valid_mean(aligned, 2)
    return {"map": image, "roi_maps": aligned, "centers": centers, "roi_support": count,
            "aligned_roi": int(np.isfinite(centers).all(axis=1).sum())}


def population_spatial(flies: list[dict]) -> dict:
    """Return [15,15] equal-fly RF plus contributing ROI and fly counts."""
    maps = np.stack([fly["map"] for fly in flies])
    image, fly_count = valid_mean(maps, 0)
    roi_count = np.sum([fly["roi_support"] for fly in flies], axis=0)
    return {"map": image, "fly_support": fly_count, "roi_support": roi_count}


def temporal_maps(estimates: list[dict], config: dict) -> tuple[np.ndarray, np.ndarray]:
    """Full-record fixed-reference diagnostic [fly,lag,15,15] and equal-fly mean."""
    flies = []
    for estimate in estimates:
        centers = temporal_reference_centers(estimate["raw_kernel"], config)
        aligned = align_temporal_reference(estimate["kernel"], centers)
        flies.append(valid_mean(aligned, 3)[0])
    fly_maps = np.stack(flies)
    return fly_maps, valid_mean(fly_maps, 0)[0]
