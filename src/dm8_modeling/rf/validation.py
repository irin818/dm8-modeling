"""Fly-level signed RF summaries and exploratory, re-centered null statistics."""

from __future__ import annotations

import numpy as np

from .population import image_correlation, radial_profile, shift_to_center, valid_mean, zone_means


def align_temporal_bins(kernel: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Use one recording-derived center for all bins; cropped pixels stay NaN."""
    return np.stack([shift_to_center(image, centers)[0] for image in kernel])


def fly_mean_bins(aligned: np.ndarray, membership: np.ndarray) -> np.ndarray:
    """Equal ROI weights per valid pixel; empty groups remain missing."""
    return valid_mean(aligned[:, :, :, membership], axis=3)[0]


def summarize_map(image: np.ndarray, config: dict) -> dict:
    center, surround = zone_means(image, config['center_zone_radius_px'],
                                  config['surround_zone_inner_px'], config['surround_zone_outer_px'])
    rows, cols = np.mgrid[:15, :15]
    mask = np.hypot(rows - 7, cols - 7) <= config['center_zone_radius_px']
    central = image[mask & np.isfinite(image)]
    radial = radial_profile(image, np.asarray(config['radial_edges_pixels']))[0]
    return {'center_zone': center, 'surround_zone': surround,
            'center_pixel': float(image[7, 7]),
            'max_central_magnitude': float(np.max(np.abs(central))) if len(central) else np.nan,
            'radial_profile': radial}


def cancellation(values: np.ndarray, axis: int = 0) -> np.ndarray:
    """1-|mean|/mean(|value|): 0 no sign cancellation, 1 complete cancellation."""
    mean, _ = valid_mean(values, axis)
    magnitude, _ = valid_mean(np.abs(values), axis)
    ratio = np.divide(np.abs(mean), magnitude, out=np.full_like(mean, np.nan), where=magnitude > 1e-12)
    return np.clip(1 - ratio, 0, 1)


def consensus(maps: np.ndarray) -> dict[str, np.ndarray]:
    """Count exact positive/negative signs; this is not a significance map."""
    negative = np.sum(np.isfinite(maps) & (maps < 0), axis=0)
    positive = np.sum(np.isfinite(maps) & (maps > 0), axis=0)
    count = np.sum(np.isfinite(maps), axis=0)
    signed_majority = np.where(negative > positive, -negative,
                               np.where(positive > negative, positive, 0))
    return {'negative_count': negative, 'positive_count': positive, 'valid_fly_count': count,
            'signed_majority': signed_majority, 'sign_mixed': (negative > 0) & (positive > 0)}


def empirical_test(observed: float, null: np.ndarray, tail: str = 'negative') -> dict:
    values = np.asarray(null)[np.isfinite(null)]
    if not np.isfinite(observed) or not len(values):
        return {'p': None, 'n_valid': len(values), 'extreme_count': None, 'null_quantiles': [None] * 3}
    if tail == 'negative':
        extreme = values <= observed
    elif tail == 'magnitude':
        extreme = values >= observed
    else:
        raise ValueError('Use negative or magnitude tail')
    count = int(extreme.sum())
    return {'p': (1 + count) / (len(values) + 1), 'n_valid': len(values),
            'extreme_count': count, 'null_quantiles': np.quantile(values, [.025, .5, .975]).tolist()}


def radial_extremes(profile: np.ndarray, edges: np.ndarray, min_edge: float) -> dict:
    index = np.flatnonzero((edges[:-1] >= min_edge) & np.isfinite(profile))
    if not len(index):
        return {'peak_radius_px': None, 'peak_amplitude': None,
                'positive_peak_radius_px': None, 'positive_peak_amplitude': None,
                'negative_peak_radius_px': None, 'negative_peak_amplitude': None}
    radius = (edges[:-1] + edges[1:]) / 2
    peak = index[np.argmax(np.abs(profile[index]))]
    positive = index[profile[index] > 0]
    negative = index[profile[index] < 0]
    pos = positive[np.argmax(profile[positive])] if len(positive) else None
    neg = negative[np.argmin(profile[negative])] if len(negative) else None
    return {'peak_radius_px': float(radius[peak]), 'peak_amplitude': float(profile[peak]),
            'positive_peak_radius_px': float(radius[pos]) if pos is not None else None,
            'positive_peak_amplitude': float(profile[pos]) if pos is not None else None,
            'negative_peak_radius_px': float(radius[neg]) if neg is not None else None,
            'negative_peak_amplitude': float(profile[neg]) if neg is not None else None}


def vector_correlation(first: np.ndarray, second: np.ndarray) -> float | None:
    return image_correlation(np.asarray(first), np.asarray(second))
