"""Summarize saved held-out pixel-model predictions and draw one example."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def score(actual: np.ndarray, prediction: np.ndarray) -> tuple[float, float]:
    r = float(np.corrcoef(actual, prediction)[0, 1])
    r2 = float(1 - np.sum((actual - prediction) ** 2) / np.sum((actual - actual.mean()) ** 2))
    return r, r2


def block_bootstrap(
    actual: np.ndarray, prediction: np.ndarray, block_length: int = 68,
    repetitions: int = 2000, seed: int = 20260929,
) -> dict:
    """Paired moving-block resampling of the untouched test predictions."""
    n = len(actual)
    rng = np.random.default_rng(seed)
    estimates = np.empty((repetitions, 2))
    blocks = int(np.ceil(n / block_length))
    for iteration in range(repetitions):
        starts = rng.integers(0, n - block_length + 1, size=blocks)
        indices = (starts[:, None] + np.arange(block_length)).ravel()[:n]
        estimates[iteration] = score(actual[indices], prediction[indices])
    ci = np.quantile(estimates, [0.025, 0.975], axis=0)
    return {"test_r_95pct_block_bootstrap_ci": ci[:, 0].tolist(),
            "test_r2_95pct_block_bootstrap_ci": ci[:, 1].tolist(),
            "block_length_frames": block_length, "bootstrap_repetitions": repetitions, "seed": seed}


def _polyline(x: np.ndarray, y: np.ndarray, box: tuple[int, int, int, int],
              y_min: float, y_max: float) -> str:
    left, top, width, height = box
    xx = left + (x - x.min()) / max(float(np.ptp(x)), 1e-9) * width
    yy = top + height - (y - y_min) / max(y_max - y_min, 1e-9) * height
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(xx, yy, strict=True))


def render_svg(path: Path, row: dict, weights: np.ndarray,
               time: np.ndarray, actual: np.ndarray, predicted: np.ndarray) -> None:
    """Write a small standalone vector figure with no plotting dependency."""
    lag = np.arange(len(weights)) / 15
    t = (time - time[0]) / 1e6
    shown = t <= 20
    trace_min = float(min(actual[shown].min(), predicted[shown].min()))
    trace_max = float(max(actual[shown].max(), predicted[shown].max()))
    filter_min = float(min(weights.min(), 0))
    filter_max = float(max(weights.max(), 0))
    selected_x = 68 + row["pixel_col_zero_based"] * 13
    selected_y = 100 + row["pixel_row_zero_based"] * 13
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360">',
        '<rect width="1200" height="360" fill="white"/>',
        '<g font-family="Arial,sans-serif" fill="#222" font-size="14">',
        '<text x="55" y="42" font-size="18">Training-selected stimulus pixel</text>',
        '<text x="342" y="42" font-size="18">Temporal filter</text>',
        '<text x="702" y="42" font-size="18">Held-out response: first 20 s</text>',
        '<text x="70" y="322">Stored column</text>',
        '<text x="350" y="322">Lag after stimulus update (s)</text>',
        '<text x="705" y="322">Time in test block (s)</text>',
        f'<text x="55" y="77">row {row["pixel_row_zero_based"]}, col {row["pixel_col_zero_based"]}</text>',
        f'<text x="342" y="77">raw intensity / stimulus unit</text>',
        f'<text x="702" y="77">raw ROI mean intensity</text>',
        f'<rect x="{selected_x}" y="{selected_y}" width="13" height="13" fill="#205e9b"/>',
        '<rect x="68" y="100" width="195" height="195" fill="none" stroke="#999"/>',
        '<rect x="342" y="100" width="280" height="195" fill="none" stroke="#999"/>',
        '<rect x="702" y="100" width="450" height="195" fill="none" stroke="#999"/>',
        f'<polyline fill="none" stroke="#205e9b" stroke-width="2" points="{_polyline(lag, weights, (342,100,280,195), filter_min, filter_max)}"/>',
        f'<polyline fill="none" stroke="#999" stroke-width="1" points="{_polyline(t[shown], actual[shown], (702,100,450,195), trace_min, trace_max)}"/>',
        f'<polyline fill="none" stroke="#205e9b" stroke-width="1.8" points="{_polyline(t[shown], predicted[shown], (702,100,450,195), trace_min, trace_max)}"/>',
        '<text x="900" y="85" fill="#999">recorded</text><text x="1040" y="85" fill="#205e9b">predicted</text>',
        f'<text x="702" y="308">0</text><text x="1128" y="308">20</text>',
        f'<text x="342" y="308">0</text><text x="590" y="308">{lag[-1]:.2f}</text>',
        '</g></svg>',
    ]
    path.write_text("\n".join(svg))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("outputs/pixel_raw"))
    parser.add_argument("--example-fly", default="fly1")
    parser.add_argument("--example-roi", default="Mean29")
    args = parser.parse_args()
    sources = sorted(args.results_dir.glob("fly*/*/pixel_metrics.json"))
    if not sources:
        raise FileNotFoundError("No pixel_metrics.json files found")
    summary = {"session_count": len(sources), "roi_count": 0, "sessions": [],
               "validation_r2_above_0_05": 0, "validated_positive_test_r2": 0,
               "positive_test_r2_and_shift_q_below_0_05": 0}
    example = None
    for path in sources:
        report = json.loads(path.read_text())
        rows = report["roi_metrics"]
        summary["roi_count"] += len(rows)
        summary["validation_r2_above_0_05"] += sum(row["validation_r2"] > 0.05 for row in rows)
        summary["validated_positive_test_r2"] += sum(
            row["validation_r2"] > 0.05 and row["test_r2"] > 0 for row in rows)
        summary["positive_test_r2_and_shift_q_below_0_05"] += sum(
            row["test_r2"] > 0 and row["shift_null_q_all_rois"] < 0.05 for row in rows)
        summary["sessions"].append({"fly": report["fly"], "run_id": report["run_id"],
                                    "roi_count": len(rows), "median_test_r2": report["median_test_r2"],
                                    "positive_test_r2": sum(row["test_r2"] > 0 for row in rows)})
        if report["fly"] == args.example_fly:
            matches = [j for j, row in enumerate(rows) if row["roi"] == args.example_roi]
            if len(matches) != 1:
                raise ValueError("Example ROI missing or duplicated")
            example = (path, report, matches[0])
    if example is None:
        raise ValueError("Example fly not found")
    path, report, j = example
    row = report["roi_metrics"][j]
    with np.load(path.with_name("pixel_model.npz")) as data:
        actual = data["test_actual"][:, j].astype(float)
        predicted = data["test_predicted"][:, j].astype(float)
        time = data["test_time_us"].astype(float)
        weights = data["coefficients"][j].astype(float)
    half = len(actual) // 2
    summary["example"] = {"fly": report["fly"], "run_id": report["run_id"], **row,
                          "test_first_half_r_r2": score(actual[:half], predicted[:half]),
                          "test_second_half_r_r2": score(actual[half:], predicted[half:]),
                          "temporal_coefficients": weights.tolist(),
                          **block_bootstrap(actual, predicted)}
    (args.results_dir / "validation.json").write_text(json.dumps(summary, indent=2, allow_nan=False))

    render_svg(args.results_dir / "example_pixel_model.svg", row, weights, time, actual, predicted)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
