"""Explore fixed-model held-out sensitivity to effective Zeiss/DLP offsets.

The original model remains fitted at zero offset. This is an ESTIMATED timing
sensitivity check, not an exposure-onset calibration or an offset correction.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from dm8_modeling.data import align_session, discover_sessions
from dm8_modeling.model import _scores
from dm8_modeling.pixel import predict_pixel_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--pixel-results-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for session in discover_sessions(args.data_root):
        aligned = align_session(session)
        path = args.pixel_results_dir / session.fly / session.run_id / "pixel_model.npz"
        with np.load(path, allow_pickle=False) as fitted:
            actual = fitted["test_actual"]
            times = fitted["test_time_us"]
            coefficients = fitted["coefficients"]
            pixels = fitted["selected_pixels"]
            intercepts = fitted["intercepts"]
            stored = fitted["test_predicted"]
        history = coefficients.shape[1]
        # Keep one conservative common subset across all tested offsets.
        common = (aligned.update_index >= history + 8) & (aligned.update_index < len(aligned.stimulus) - 8)
        common_times = aligned.imaging_time_us[common]
        common_y = aligned.response[common].astype(np.float64)
        half = int(len(common_y) * .35)
        early_end = int(len(common_y) * .7)
        for offset_ms in range(-500, 501, 50):
            index = np.searchsorted(aligned.update_time_us, times + offset_ms * 1000, side="right") - 1
            prediction = predict_pixel_model(aligned.stimulus, index, coefficients, pixels, intercepts)
            if offset_ms == 0 and not np.allclose(prediction, stored, rtol=0, atol=1e-10):
                raise ValueError("Zero-offset replay differs from saved prediction")
            r, r2 = _scores(actual, prediction)
            common_index = np.searchsorted(aligned.update_time_us, common_times + offset_ms * 1000, side="right") - 1
            histories = aligned.stimulus[
                common_index[:, None, None] - np.arange(history)[None, :, None], pixels[None, None, :]
            ].astype(np.float64)
            first_x, second_x = histories[:half], histories[half:early_end]
            first_y, second_y = common_y[:half], common_y[half:early_end]
            k1 = np.einsum("nlr,nr->lr", first_x - first_x.mean(axis=0), first_y - first_y.mean(axis=0)) / len(first_x)
            k2 = np.einsum("nlr,nr->lr", second_x - second_x.mean(axis=0), second_y - second_y.mean(axis=0)) / len(second_x)
            k1c, k2c = k1 - k1.mean(axis=0), k2 - k2.mean(axis=0)
            denominator = np.linalg.norm(k1c, axis=0) * np.linalg.norm(k2c, axis=0)
            reliability = np.divide(np.sum(k1c * k2c, axis=0), denominator,
                                    out=np.zeros(len(pixels)), where=denominator > 0)
            strength = np.linalg.norm(k1, axis=0)
            rows.append({"fly": session.fly, "run_id": session.run_id, "effective_offset_ms": offset_ms,
                         "median_test_r": float(np.nanmedian(r)), "median_test_r2": float(np.nanmedian(r2)),
                         "positive_r_roi_count": int(np.sum(r > 0)),
                         "median_selected_pixel_filter_strength": float(np.median(strength)),
                         "median_selected_pixel_split_half_r": float(np.median(reliability))})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / "timing_offset_sensitivity.csv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    by_fly = {fly: max((row for row in rows if row["fly"] == fly), key=lambda row: row["median_test_r"])
              for fly in sorted({row["fly"] for row in rows})}
    print(json.dumps(by_fly, indent=2))


if __name__ == "__main__":
    main()
