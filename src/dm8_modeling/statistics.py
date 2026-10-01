"""Exploratory final-pipeline circular-shift validation at the five-fly level."""

import numpy as np
from .rf import estimate_strf, global_energy_lag, zone_means
from .population import fly_spatial, population_spatial


def circular_shifts(frame_count: int, interval_us: float, config: dict, rng) -> np.ndarray:
    """Draw [iteration] frame offsets at least 60s from zero in either direction."""
    minimum = int(np.ceil(config["minimum_null_shift_seconds"]*1_000_000/interval_us))
    if frame_count <= 2*minimum:
        raise ValueError("Recording too short for the null shift exclusion")
    return rng.integers(minimum,frame_count-minimum+1,size=config["null_iterations"])


def empirical_p(observed: float, values: np.ndarray, *, positive: bool = False) -> float:
    """Plus-one one-sided empirical p from finite null values; not external validation."""
    values = values[np.isfinite(values)]
    if not len(values) or not np.isfinite(observed):
        raise ValueError("Finite observed and null statistics required")
    extremes = values >= observed if positive else values <= observed
    return float((1+extremes.sum())/(len(values)+1))


def full_pipeline_null(recordings: list, config: dict, observed: tuple) -> tuple[dict, np.ndarray]:
    """500 raw joint-ROI shifts; reselect full-record lag, then redo trimmed maps."""
    if config["null_iterations"] < 500:
        raise ValueError("Final reproduction requires at least 500 full-pipeline null iterations")
    rng = np.random.default_rng(config["null_seed"])
    shifts = [circular_shifts(len(r.response),float(np.median(np.diff(r.frame_us))),config,rng) for r in recordings]
    values = np.empty((config["null_iterations"],2))
    for iteration in range(config["null_iterations"]):
        full = [estimate_strf(r,config,trim=False,shift=int(s[iteration]))
                for r,s in zip(recordings,shifts,strict=True)]
        lag = global_energy_lag(full)
        trimmed = [estimate_strf(r,config,trim=True,shift=int(s[iteration]))
                   for r,s in zip(recordings,shifts,strict=True)]
        population = population_spatial([fly_spatial(item,lag,config) for item in trimmed])
        values[iteration] = zone_means(population["map"],config)
        if (iteration+1) % 50 == 0:
            print(f"Full-pipeline null {iteration+1}/{config['null_iterations']}",flush=True)
    summary = {"iterations":len(values),"seed":config["null_seed"],
        "minimum_shift_seconds":config["minimum_null_shift_seconds"],
        "observed_center":observed[0],"observed_surround":observed[1],
        "center_p_negative":empirical_p(observed[0],values[:,0]),
        "surround_p_positive":empirical_p(observed[1],values[:,1],positive=True),
        "center_null_quantiles":np.quantile(values[:,0],[.025,.5,.975]).tolist(),
        "surround_null_quantiles":np.quantile(values[:,1],[.025,.5,.975]).tolist()}
    return summary,values
