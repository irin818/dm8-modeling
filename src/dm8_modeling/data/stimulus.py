"""Validate the frozen binary digital stimulus against its saved recipe.

The ±1 analysis code corresponds to 0/100 digital gray in these five runs;
this does not measure light delivered at the fly.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_binary_stimulus_package(recipe: dict, package: dict[str, np.ndarray]) -> dict:
    """Check the saved binary sequence against its own seed and digital levels."""
    if recipe.get("stimulus_family") != "binary_discrete_time":
        raise ValueError("Only binary_discrete_time stimulus packages are supported")
    updates = package["stimulus_updates_rc_float32"]
    gray = package["stimulus_updates_display_gray_uint8"]
    display = package["display_frames_gray_uint8"]
    start = package["update_start_display_frame_idx_int32"]
    rendering = recipe["rendering"]
    dark, bright = int(rendering["dark_level"]), int(rendering["bright_level"])
    if not 0 <= dark < bright <= 255 or updates.shape != gray.shape:
        raise ValueError("Invalid digital gray levels or update shapes")
    probability = float(recipe["family_parameters"]["binary_bright_probability"])
    if not 0 <= probability <= 1:
        raise ValueError("Invalid binary bright probability")
    expected = np.where(
        np.random.RandomState(int(recipe["randomization"]["seed"]))
        .random_sample(updates.shape) < probability,
        1.0, -1.0,
    ).astype(np.float32)
    expected_gray = np.where(expected > 0, bright, dark).astype(np.uint8)
    if len(start) != len(updates) or np.any(start < 0) or np.any(start >= len(display)):
        raise ValueError("Invalid display-frame indices for stimulus updates")
    if not np.array_equal(updates, expected):
        raise ValueError("Frozen binary stimulus differs from recipe seed reconstruction")
    if not np.array_equal(gray, expected_gray):
        raise ValueError("Frozen stimulus digital gray does not match ±1 coding")
    if not np.array_equal(display[start], gray):
        raise ValueError("Display frames differ from frozen update gray levels")
    return {
        "seed_reconstruction_passed": True,
        "digital_gray_mapping_passed": True,
        "minus_one_commanded_gray": dark,
        "plus_one_commanded_gray": bright,
        "digital_color_channel": str(rendering["color_channel"]),
        "stimulus_seed": int(recipe["randomization"]["seed"]),
        "nominal_pixel_width_deg": float(recipe["geometry"]["summary"]["derived"]["actual_cell_width_deg"]),
        "nominal_pixel_height_deg": float(recipe["geometry"]["summary"]["derived"]["actual_cell_height_deg"]),
    }
