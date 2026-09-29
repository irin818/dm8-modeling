"""Compact convolutional residual model over a frozen linear pixel baseline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from ...data import AlignedSession
from ...evaluation.legacy_metrics import _finite_or_none, _scores
from ...features.lagged import lagged_design
from ..linear.pixel_temporal import _fit


class CompactResidualCNN(nn.Module):
    """Two spatial convolutions, a nonlinear head, and a fixed linear skip."""

    def __init__(self, lag_count: int, roi_count: int) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(lag_count, 4, kernel_size=3, padding=1),
            nn.ELU(),
            nn.Conv2d(4, 4, kernel_size=3, padding=1),
            nn.ELU(),
            nn.AvgPool2d(kernel_size=2, stride=2),
            nn.Flatten(),
        )
        self.head = nn.Sequential(nn.Linear(4 * 7 * 7, 16), nn.ELU(), nn.Linear(16, roi_count))
        nn.init.zeros_(self.head[-1].weight)
        nn.init.zeros_(self.head[-1].bias)
        self.register_buffer("skip_weights", torch.zeros(roi_count, lag_count))
        self.register_buffer("skip_bias", torch.zeros(roi_count))

    def set_skip(self, weights: np.ndarray, bias: np.ndarray) -> None:
        with torch.no_grad():
            self.skip_weights.copy_(torch.as_tensor(weights, dtype=torch.float32))
            self.skip_bias.copy_(torch.as_tensor(bias, dtype=torch.float32))

    def forward(self, images: torch.Tensor, center_history: torch.Tensor) -> torch.Tensor:
        linear = torch.einsum("brl,rl->br", center_history, self.skip_weights) + self.skip_bias
        return linear + self.head(self.features(images))


@dataclass
class CNNResult:
    report: dict
    model_state: dict[str, torch.Tensor]
    test_actual: np.ndarray
    test_predicted: np.ndarray
    test_baseline_predicted: np.ndarray
    test_time_us: np.ndarray


def predict_compact_cnn(
    stimulus: np.ndarray,
    update_index: np.ndarray,
    state_dict: dict[str, torch.Tensor],
    selected_pixels: np.ndarray,
    fit_mean: np.ndarray,
    fit_sd: np.ndarray,
    batch_size: int = 256,
) -> np.ndarray:
    """Predict raw ROI intensity from stimulus history and saved weights only."""
    selected = np.asarray(selected_pixels, dtype=np.int64)
    mean = np.asarray(fit_mean, dtype=np.float64)
    sd = np.asarray(fit_sd, dtype=np.float64)
    if stimulus.ndim != 2 or stimulus.shape[1] != 225 or selected.ndim != 1:
        raise ValueError("Expected 15x15 flattened stimulus and one pixel per ROI")
    if mean.shape != selected.shape or sd.shape != selected.shape or np.any(sd <= 0):
        raise ValueError("Saved ROI scaling does not match the selected pixels")
    if np.any(selected < 0) or np.any(selected >= 225) or batch_size < 1:
        raise ValueError("Invalid selected pixel or batch size")
    lag = int(state_dict["skip_weights"].shape[1])
    model = CompactResidualCNN(lag, len(selected))
    model.load_state_dict(state_dict)
    model.eval()
    design = lagged_design(stimulus, update_index, lag)
    images = torch.from_numpy(design.reshape(len(design), lag, 15, 15).copy())
    centers = torch.from_numpy(design.reshape(len(design), lag, 225)[:, :, selected].transpose(0, 2, 1).copy())
    with torch.no_grad():
        scaled = np.concatenate([
            model(images[start:start + batch_size], centers[start:start + batch_size]).numpy()
            for start in range(0, len(images), batch_size)
        ], axis=0)
    return scaled.astype(np.float64) * sd + mean


def _make_model(lag_count: int, roi_count: int, seed: int,
                weights: np.ndarray, bias: np.ndarray) -> CompactResidualCNN:
    torch.manual_seed(seed)
    model = CompactResidualCNN(lag_count, roi_count)
    model.set_skip(weights, bias)
    return model


def _train_epochs(model: CompactResidualCNN, images: torch.Tensor,
                  center: torch.Tensor, target: torch.Tensor, rows: np.ndarray,
                  optimizer: torch.optim.Optimizer, epochs: int, batch_size: int,
                  rng: np.random.Generator) -> None:
    model.train()
    for _ in range(epochs):
        for batch in np.array_split(rng.permutation(rows), max(1, int(np.ceil(len(rows) / batch_size)))):
            optimizer.zero_grad(set_to_none=True)
            prediction = model(images[batch], center[batch])
            loss = torch.mean((prediction - target[batch]) ** 2)
            loss.backward()
            optimizer.step()


def fit_compact_cnn(
    aligned: AlignedSession,
    baseline_report: dict,
    baseline_model: dict[str, np.ndarray],
    max_epochs: int = 60,
    patience: int = 10,
    batch_size: int = 256,
    learning_rate: float = 0.001,
    weight_decay: float = 0.001,
    seed: int = 20260929,
) -> CNNResult:
    """Tune CNN epochs on the pixel model's validation block; score same test.

    The fixed skip is refit on training rows for epoch selection and restored
    from the saved pixel model for the final training-plus-validation fit.
    The CNN never sees response rows from the held-out test block.
    """
    if max_epochs < 1 or patience < 1 or batch_size < 1 or learning_rate <= 0 or weight_decay < 0:
        raise ValueError("Invalid CNN training settings")
    torch.set_num_threads(min(torch.get_num_threads(), 4))
    lag = int(baseline_report["lag_count"])
    n_roi = len(aligned.roi_labels)
    labels = [str(label) for label in baseline_model["roi_labels"]]
    if labels != aligned.roi_labels or len(baseline_report["roi_metrics"]) != n_roi:
        raise ValueError("Baseline ROI labels differ from aligned data")
    selected = np.asarray(baseline_model["selected_pixels"], dtype=np.int64)
    coefficients = np.asarray(baseline_model["coefficients"], dtype=np.float64)
    intercepts = np.asarray(baseline_model["intercepts"], dtype=np.float64)
    eligible = aligned.update_index >= lag - 1
    indices = aligned.update_index[eligible]
    y = aligned.response[eligible].astype(np.float32)
    times = aligned.imaging_time_us[eligible]
    n = len(y)
    train_end = int(baseline_report["train_frames"])
    val_start = train_end + int(baseline_report["purge_frames_each"])
    val_end = val_start + int(baseline_report["validation_frames"])
    test_start = val_end + int(baseline_report["purge_frames_each"])
    if n != baseline_report["eligible_frames"] or n - test_start != baseline_report["test_frames"]:
        raise ValueError("CNN and pixel baseline must use identical time splits")
    fit_rows = np.r_[0:train_end, val_start:val_end]
    design = lagged_design(aligned.stimulus, indices, lag)
    images = torch.from_numpy(design.reshape(n, lag, 15, 15).copy())
    center_array = design.reshape(n, lag, 225)[:, :, selected].transpose(0, 2, 1).copy()
    center = torch.from_numpy(center_array)
    target = torch.from_numpy(y)
    train_mean = y[:train_end].mean(axis=0, dtype=np.float64)
    train_sd = y[:train_end].std(axis=0, dtype=np.float64)
    train_sd = np.where(train_sd > 1e-6, train_sd, 1.0)
    target_train_scaled = (target - torch.as_tensor(train_mean, dtype=torch.float32)) / torch.as_tensor(train_sd, dtype=torch.float32)

    train_coefficients = np.empty_like(coefficients)
    train_intercepts = np.empty_like(intercepts)
    for roi, entry in enumerate(baseline_report["roi_metrics"]):
        beta, bias = _fit(center_array[:train_end, roi, :], y[:train_end, roi], float(entry["selected_penalty"]))
        train_coefficients[roi] = beta
        train_intercepts[roi] = bias
    model = _make_model(lag, n_roi, seed, train_coefficients / train_sd[:, None],
                        (train_intercepts - train_mean) / train_sd)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    rng = np.random.default_rng(seed)
    validation_rows = np.arange(val_start, val_end)
    with torch.no_grad():
        model.eval()
        best_loss = float(torch.mean((model(images[validation_rows], center[validation_rows])
                                      - target_train_scaled[validation_rows]) ** 2))
    best_epoch = 0
    wait = 0
    training_curve = [{"epoch": 0, "validation_scaled_mse": best_loss}]
    train_rows = np.arange(train_end)
    for epoch in range(1, max_epochs + 1):
        _train_epochs(model, images, center, target_train_scaled, train_rows,
                      optimizer, 1, batch_size, rng)
        model.eval()
        with torch.no_grad():
            loss = float(torch.mean((model(images[validation_rows], center[validation_rows])
                                     - target_train_scaled[validation_rows]) ** 2))
        training_curve.append({"epoch": epoch, "validation_scaled_mse": loss})
        if loss < best_loss - 1e-5:
            best_loss = loss
            best_epoch = epoch
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break
    # Only the epoch count is selected. The final fit starts afresh on the
    # combined training and validation blocks with the frozen pixel baseline.

    fit_mean = y[fit_rows].mean(axis=0, dtype=np.float64)
    fit_sd = y[fit_rows].std(axis=0, dtype=np.float64)
    fit_sd = np.where(fit_sd > 1e-6, fit_sd, 1.0)
    target_fit_scaled = (target - torch.as_tensor(fit_mean, dtype=torch.float32)) / torch.as_tensor(fit_sd, dtype=torch.float32)
    final_model = _make_model(lag, n_roi, seed, coefficients / fit_sd[:, None],
                              (intercepts - fit_mean) / fit_sd)
    if best_epoch > 0:
        final_optimizer = torch.optim.AdamW(final_model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        _train_epochs(final_model, images, center, target_fit_scaled, fit_rows,
                      final_optimizer, best_epoch, batch_size, np.random.default_rng(seed))
    final_model.eval()
    test_rows = np.arange(test_start, n)
    with torch.no_grad():
        scaled_prediction = np.concatenate([
            final_model(images[batch], center[batch]).numpy()
            for batch in np.array_split(test_rows, max(1, int(np.ceil(len(test_rows) / batch_size))))
        ], axis=0)
    baseline_prediction = np.asarray(baseline_model["test_predicted"], dtype=np.float64)
    prediction = (scaled_prediction.astype(np.float64) * fit_sd + fit_mean
                  if best_epoch else baseline_prediction.copy())
    actual = y[test_start:].astype(np.float64)
    if baseline_prediction.shape != prediction.shape or not np.array_equal(actual.astype(np.float32), baseline_model["test_actual"]):
        raise ValueError("Saved pixel test data differs from aligned CNN test block")
    cnn_r, cnn_r2 = _scores(actual, prediction)
    pixel_r, pixel_r2 = _scores(actual, baseline_prediction)
    roi_metrics = []
    for roi, label in enumerate(aligned.roi_labels):
        roi_metrics.append({
            "roi": label,
            "pixel_test_r": _finite_or_none(pixel_r[roi]),
            "pixel_test_r2": _finite_or_none(pixel_r2[roi]),
            "cnn_test_r": _finite_or_none(cnn_r[roi]),
            "cnn_test_r2": _finite_or_none(cnn_r2[roi]),
            "cnn_minus_pixel_test_r2": _finite_or_none(cnn_r2[roi] - pixel_r2[roi]),
        })
    report = {
        "fly": aligned.session.fly,
        "run_id": aligned.session.run_id,
        "model": "two_convolution_residual_CNN_with_frozen_pixel_linear_skip",
        "response_kind": "raw_ROI_mean_intensity",
        "architecture": "18x15x15 -> conv(4,3x3) -> ELU -> conv(4,3x3) -> ELU -> avgpool(2) -> dense(16) -> ELU -> ROI residual + frozen linear pixel model",
        "trainable_parameter_count": int(sum(parameter.numel() for parameter in final_model.parameters())),
        "baseline_train_selected_pixels": selected.tolist(),
        "lag_count": lag,
        "train_frames": train_end,
        "validation_frames": len(validation_rows),
        "test_frames": len(test_rows),
        "purge_frames_each": int(baseline_report["purge_frames_each"]),
        "train_time_us": baseline_report["train_time_us"],
        "validation_time_us": baseline_report["validation_time_us"],
        "test_time_us": baseline_report["test_time_us"],
        "max_epochs": max_epochs,
        "patience": patience,
        "selected_epoch": best_epoch,
        "selected_validation_scaled_mse": best_loss,
        "training_curve": training_curve,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "weight_decay": weight_decay,
        "seed": seed,
        "fit_mean": fit_mean.tolist(),
        "fit_sd": fit_sd.tolist(),
        "median_pixel_test_r2": _finite_or_none(np.nanmedian(pixel_r2)),
        "median_cnn_test_r2": _finite_or_none(np.nanmedian(cnn_r2)),
        "roi_cnn_better_by_0p01_r2_count": int(np.sum(cnn_r2 - pixel_r2 > 0.01)),
        "roi_cnn_worse_by_0p01_r2_count": int(np.sum(cnn_r2 - pixel_r2 < -0.01)),
        "roi_metrics": roi_metrics,
        "interpretation_limit": "The CNN is a flexible benchmark on the existing time split; its residual branch is less directly interpretable than the frozen linear skip. Model-family selection has seen earlier test results.",
    }
    return CNNResult(report, {key: value.cpu().clone() for key, value in final_model.state_dict().items()},
                     actual, prediction, baseline_prediction, times[test_start:])
