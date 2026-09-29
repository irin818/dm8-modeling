"""Per-ROI trace and hardware-clock quality summaries (no model fitting).

Input raw Results.csv [frame,ROI] and TTL microseconds; output per-ROI and
per-clock derived statistics. Clipping counts are not calibrated ADC saturation.
"""
from __future__ import annotations
import numpy as np

def _corr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a - a.mean(axis=0)
    b = b - b.mean(axis=0)
    denominator = np.sqrt(np.sum(a * a, axis=0) * np.sum(b * b, axis=0))
    return np.divide(np.sum(a * b, axis=0), denominator, out=np.zeros(a.shape[1]), where=denominator > 0)


def _clock_summary(name: str, values: np.ndarray, expected_us: float | None) -> dict:
    intervals = np.diff(values)
    median = float(np.median(intervals))
    return {
        "clock": name, "count": len(values), "start_us": int(values[0]), "end_us": int(values[-1]),
        "duplicate_or_reverse": int(np.sum(intervals <= 0)), "median_interval_us": median,
        "p01_interval_us": float(np.quantile(intervals, .01)),
        "p99_interval_us": float(np.quantile(intervals, .99)),
        "max_interval_us": int(np.max(intervals)),
        "intervals_over_1p5x_median": int(np.sum(intervals > 1.5 * median)),
        "nominal_interval_us": expected_us,
    }


def _response_rows(fly: str, run_id: str, response: np.ndarray, labels: list[str], fs_hz: float) -> list[dict]:
    rows = []
    count = len(response)
    first = response[:count // 10]
    last = response[-count // 10:]
    for idx, label in enumerate(labels):
        signal = response[:, idx].astype(np.float64)
        mean = float(np.mean(signal))
        std = float(np.std(signal))
        median = float(np.median(signal))
        mad = float(np.median(np.abs(signal - median)))
        step = np.diff(signal)
        jump_scale = float(np.median(np.abs(step - np.median(step))))
        frequencies = np.fft.rfftfreq(count, 1 / fs_hz)
        power = np.abs(np.fft.rfft(signal - mean)) ** 2
        power[0] = 0
        peak_hz = float(frequencies[int(np.argmax(power))])
        rows.append({
            "fly": fly, "run_id": run_id, "roi": label, "count": count,
            "mean": mean, "median": median, "std": std, "cv": std / mean if mean else "",
            "min": float(np.min(signal)), "p01": float(np.quantile(signal, .01)),
            "p05": float(np.quantile(signal, .05)), "p95": float(np.quantile(signal, .95)),
            "p99": float(np.quantile(signal, .99)), "max": float(np.max(signal)),
            "zero_count": int(np.sum(signal == 0)),
            "at_max_count": int(np.sum(signal == np.max(signal))),
            "first_last_decile_change_fraction": float((np.mean(last[:, idx]) - np.mean(first[:, idx])) / mean) if mean else "",
            "robust_outlier_count": int(np.sum(np.abs(signal - median) > 6 * 1.4826 * mad)) if mad else 0,
            "abrupt_jump_count": int(np.sum(np.abs(step - np.median(step)) > 8 * 1.4826 * jump_scale)) if jump_scale else 0,
            "lag1_autocorrelation": float(_corr(signal[:-1, None], signal[1:, None])[0]),
            "psd_peak_hz": peak_hz,
        })
    return rows
