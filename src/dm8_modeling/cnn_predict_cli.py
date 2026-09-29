"""Reproduce one saved CNN test prediction using stimulus and model weights."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import torch

from .cnn import predict_compact_cnn
from .data import align_session, discover_sessions
from .model import _scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--model-file", type=Path, required=True, help="Saved cnn_model.pt")
    parser.add_argument("--roi", required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    saved = torch.load(args.model_file, map_location="cpu", weights_only=True)
    labels = saved["roi_labels"]
    if args.roi not in labels:
        parser.error(f"ROI {args.roi!r} is absent from the saved CNN")
    roi = labels.index(args.roi)
    records = np.load(args.model_file.parent / "cnn_test_predictions.npz", allow_pickle=False)
    matches = [session for session in discover_sessions(args.data_root)
               if session.fly == saved["fly"] and session.run_id == saved["run_id"]]
    if len(matches) != 1:
        parser.error("Could not identify the saved experimental run")
    aligned = align_session(matches[0])
    if aligned.qc["source_sha256"] != saved["source_sha256"]:
        parser.error("Experimental source files differ from the saved model inputs")
    eligible = aligned.update_index >= int(saved["lag_count"]) - 1
    test_start = int(saved["test_start_eligible_frame"])
    indices = aligned.update_index[eligible][test_start:]
    actual = aligned.response[eligible][test_start:, roi]
    times = aligned.imaging_time_us[eligible][test_start:]
    predicted = predict_compact_cnn(
        aligned.stimulus, indices, saved["state_dict"],
        saved["selected_pixels"], saved["fit_mean"], saved["fit_sd"],
    )[:, roi]
    if not np.allclose(predicted, records["test_cnn_predicted"][:, roi], atol=1e-5, rtol=1e-5):
        raise ValueError("Saved CNN predictions differ from independent reconstruction")
    if not np.array_equal(actual, records["test_actual"][:, roi]):
        raise ValueError("Observed test intensities differ from saved data")
    if not np.array_equal(times, records["test_time_us"]):
        raise ValueError("Test timestamps differ from saved data")
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["imaging_time_us", "cnn_predicted_roi_mean", "observed_roi_mean"])
        writer.writerows(zip(times, predicted, actual, strict=True))
    r, r2 = _scores(actual[:, None], predicted[:, None])
    print(f"{saved['fly']}/{saved['run_id']} {args.roi}: {len(predicted)} test frames, r={r[0]:.3f}, R2={r2[0]:.3f}")
    print(f"Saved {args.output_csv}")


if __name__ == "__main__":
    main()
