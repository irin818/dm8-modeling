"""Mask-aware, sign-preserving descriptive RF aggregation in pixel units."""

from __future__ import annotations

import numpy as np


def shift_to_center(maps: np.ndarray, centers: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Translate [15,15,ROI] maps to (7,7); cropped pixels remain missing."""
    if maps.ndim != 3 or maps.shape[:2] != (15, 15) or centers.shape != (maps.shape[2], 2):
        raise ValueError("Expected maps [15,15,ROI] and centers [ROI,2]")
    aligned = np.full(maps.shape, np.nan, dtype=float)
    for roi, (row, col) in enumerate(centers):
        if not np.isfinite((row, col)).all():
            continue
        dr, dc = 7 - int(np.rint(row)), 7 - int(np.rint(col))
        source_rows = slice(max(0, -dr), min(15, 15 - dr))
        source_cols = slice(max(0, -dc), min(15, 15 - dc))
        target_rows = slice(max(0, dr), min(15, 15 + dr))
        target_cols = slice(max(0, dc), min(15, 15 + dc))
        aligned[target_rows, target_cols, roi] = maps[source_rows, source_cols, roi]
    return aligned, np.isfinite(aligned)


def valid_mean(values: np.ndarray, axis: int) -> tuple[np.ndarray, np.ndarray]:
    """Average only finite contributors, reporting each pixel's denominator."""
    valid = np.isfinite(values)
    count = np.sum(valid, axis=axis)
    total = np.sum(np.where(valid, values, 0), axis=axis)
    mean = np.divide(total, count, out=np.full_like(total, np.nan, dtype=float), where=count > 0)
    return mean, count


def energy_centers(kernels: np.ndarray) -> np.ndarray:
    """Fixed sensitivity center: energy centroid over all temporal bins."""
    if kernels.ndim != 4 or kernels.shape[1:3] != (15, 15):
        raise ValueError("Expected [bin,15,15,ROI]")
    energy = np.sum(kernels * kernels, axis=0)
    weight = np.sum(energy, axis=(0, 1))
    rows, cols = np.mgrid[:15, :15]
    centers = np.column_stack((np.divide(np.sum(energy * rows[:, :, None], axis=(0, 1)), weight,
                                        out=np.full(len(weight), np.nan), where=weight > 0),
                               np.divide(np.sum(energy * cols[:, :, None], axis=(0, 1)), weight,
                                         out=np.full(len(weight), np.nan), where=weight > 0)))
    return centers


def radial_profile(image: np.ndarray, edges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if image.shape != (15, 15) or edges.ndim != 1 or np.any(np.diff(edges) <= 0):
        raise ValueError("Expected 15x15 map and increasing radial edges")
    rows, cols = np.mgrid[:15, :15]
    distance = np.hypot(rows - 7, cols - 7)
    mean = np.full(len(edges) - 1, np.nan)
    counts = np.zeros(len(mean), dtype=int)
    for index, (low, high) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
        values = image[(distance >= low) & (distance < high) & np.isfinite(image)]
        counts[index] = len(values)
        if len(values):
            mean[index] = float(np.mean(values))
    return mean, counts


def zone_means(image: np.ndarray, center_radius: float, surround_inner: float,
               surround_outer: float) -> tuple[float, float]:
    rows, cols = np.mgrid[:15, :15]
    radius = np.hypot(rows - 7, cols - 7)
    center = image[(radius <= center_radius) & np.isfinite(image)]
    surround = image[(radius >= surround_inner) & (radius <= surround_outer) & np.isfinite(image)]
    return (float(np.mean(center)) if len(center) else float("nan"),
            float(np.mean(surround)) if len(surround) else float("nan"))


def image_correlation(first: np.ndarray, second: np.ndarray) -> float | None:
    valid = np.isfinite(first) & np.isfinite(second)
    if np.sum(valid) < 3:
        return None
    a, b = first[valid], second[valid]
    if np.std(a) <= 1e-12 or np.std(b) <= 1e-12:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def pairwise_median(images: np.ndarray) -> float | None:
    """Median correlation across ROI maps [15,15,ROI], valid overlap only."""
    correlations = [r for i in range(images.shape[2]) for j in range(i + 1, images.shape[2])
                    if (r := image_correlation(images[:, :, i], images[:, :, j])) is not None]
    return float(np.median(correlations)) if correlations else None


def dog_gate(fly_maps: np.ndarray, leave_one_out: np.ndarray, config: dict) -> dict:
    """Fixed descriptive gate; not an inferential significance test."""
    centers = np.array([zone_means(fly_maps[:, :, i], config["center_zone_radius_px"],
                                   config["surround_zone_inner_px"],
                                   config["surround_zone_outer_px"]) for i in range(fly_maps.shape[2])])
    full, _ = valid_mean(fly_maps, axis=2)
    main_center, main_surround = zone_means(full, config["center_zone_radius_px"],
                                            config["surround_zone_inner_px"],
                                            config["surround_zone_outer_px"])
    center_sign = np.sign(main_center)
    surround_sign = np.sign(main_surround)
    lofo = np.array([zone_means(leave_one_out[:, :, i], config["center_zone_radius_px"],
                                config["surround_zone_inner_px"],
                                config["surround_zone_outer_px"]) for i in range(leave_one_out.shape[2])])
    passing = (np.isfinite(centers).all() and np.isfinite(lofo).all() and
               center_sign != 0 and surround_sign != 0 and center_sign == -surround_sign and
               np.sum(np.sign(centers[:, 0]) == center_sign) >= config["dog_min_same_sign_flies"] and
               np.sum(np.sign(centers[:, 1]) == surround_sign) >= config["dog_min_same_sign_flies"] and
               np.all(np.sign(lofo[:, 0]) == center_sign) and
               np.all(np.sign(lofo[:, 1]) == surround_sign))
    return {"descriptive_dog_gate": bool(passing), "population_center": main_center,
            "population_surround": main_surround, "fly_zones": centers.tolist(),
            "leave_one_out_zones": lofo.tolist()}


def fit_radial_dog(radius: np.ndarray, profile: np.ndarray) -> dict | None:
    """Fit baseline + two opposing Gaussian components on one frozen grid."""
    valid = np.isfinite(profile)
    if np.sum(valid) < 5:
        return None
    r, y = radius[valid], profile[valid]
    best = None
    for center_width in (0.75, 1.0, 1.5, 2.0, 2.5, 3.0):
        for surround_width in (3.0, 4.0, 5.0, 6.0, 8.0):
            if surround_width <= center_width:
                continue
            design = np.column_stack((np.exp(-0.5 * (r / center_width) ** 2),
                                      np.exp(-0.5 * (r / surround_width) ** 2),
                                      np.ones(len(r))))
            coefficient = np.linalg.lstsq(design, y, rcond=None)[0]
            if coefficient[0] * coefficient[1] >= 0:
                continue
            prediction = design @ coefficient
            sse = float(np.sum((y - prediction) ** 2))
            if best is None or sse < best["sse"]:
                total = float(np.sum((y - np.mean(y)) ** 2))
                best = {"center_width_px": center_width, "surround_width_px": surround_width,
                        "center_amplitude": float(coefficient[0]),
                        "surround_amplitude": float(coefficient[1]),
                        "baseline": float(coefficient[2]), "sse": sse,
                        "r2": 1 - sse / total if total > 0 else None}
    return best
