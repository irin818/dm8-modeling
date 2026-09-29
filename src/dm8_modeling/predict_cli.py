"""Reproduce a saved Dm8 pixel model's held-out prediction for one ROI."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .data import align_session, discover_sessions
from .model import _scores
from .pixel import predict_pixel_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--model-file", type=Path, required=True, help="Saved pixel_model.npz")
    parser.add_argument("--roi", required=True, help="For example Mean29")
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    with np.load(args.model_file, allow_pickle=False) as saved:
        fly = str(saved["fly"])
        run_id = str(saved["run_id"])
        labels = [str(item) for item in saved["roi_labels"]]
        if args.roi not in labels:
            parser.error(f"ROI {args.roi!r} is absent from saved model")
        roi = labels.index(args.roi)
        coefficients = saved["coefficients"]
        intercepts = saved["intercepts"]
        pixels = saved["selected_pixels"]
        lag_count = int(saved["lag_count"])
        test_start = int(saved["test_start_eligible_frame"])
        stimulus_hash = str(saved["stimulus_sha256"])
        source_hashes = json.loads(str(saved["source_sha256_json"]))
        expected = saved["test_predicted"][:, roi]
        expected_actual = saved["test_actual"][:, roi]

    matches = [session for session in discover_sessions(args.data_root)
               if session.fly == fly and session.run_id == run_id]
    if len(matches) != 1:
        parser.error(f"Could not identify saved session {fly}/{run_id} in data root")
    aligned = align_session(matches[0])
    if aligned.qc["source_sha256"]["stim_realized.npz"] != stimulus_hash:
        parser.error("Frozen stimulus hash differs from the model's training source")
    if aligned.qc["source_sha256"] != source_hashes:
        parser.error("Model source files differ from the saved training inputs")
    eligible = aligned.update_index >= lag_count - 1
    indices = aligned.update_index[eligible][test_start:]
    times = aligned.imaging_time_us[eligible][test_start:]
    actual = aligned.response[eligible][test_start:, roi]
    if actual.shape != expected_actual.shape or not np.array_equal(actual, expected_actual):
        raise ValueError("Observed test ROI differs from the saved training source")
    prediction = predict_pixel_model(
        aligned.stimulus, indices, coefficients, pixels, intercepts,
    )[:, roi]
    if prediction.shape != expected.shape or not np.allclose(prediction, expected, atol=1e-9, rtol=1e-9):
        raise ValueError("Saved test prediction and independently reconstructed prediction differ")
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["imaging_time_us", "predicted_roi_mean", "observed_roi_mean"])
        writer.writerows(zip(times, prediction, actual, strict=True))
    r, r2 = _scores(actual[:, None], prediction[:, None])
    print(f"{fly}/{run_id} {args.roi}: {len(prediction)} held-out frames, r={r[0]:.3f}, R2={r2[0]:.3f}")
    print(f"Saved {args.output_csv}")


if __name__ == "__main__":
    main()
