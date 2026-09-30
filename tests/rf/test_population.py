"""Phase 6.2 controls for full-recording scope and fly-aware RF geometry."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from dm8_modeling.experiments.phase62 import _one_fly
from dm8_modeling.rf.population import (dog_gate, fit_radial_dog, radial_profile,
                                        shift_to_center, valid_mean)


class PopulationRFTests(unittest.TestCase):
    def test_shift_crops_without_wrap_and_counts_valid_pixels(self) -> None:
        image = np.arange(225, dtype=float).reshape(15, 15, 1)
        aligned, mask = shift_to_center(image, np.array([[0., 0.]]))
        self.assertEqual(aligned[7, 7, 0], image[0, 0, 0])
        self.assertEqual(aligned[14, 14, 0], image[7, 7, 0])
        self.assertFalse(mask[0, 0, 0])
        self.assertTrue(np.isnan(aligned[0, 0, 0]))
        self.assertEqual(mask[:, :, 0].sum(), 64)

    def test_fly_equal_weight_differs_from_pooled_roi_weight(self) -> None:
        roi_maps = np.array([[[1., 3.]], [[10., np.nan]]]).reshape(1, 1, 2, 2)
        fly1, count1 = valid_mean(roi_maps[:, :, 0], axis=2)
        fly2, count2 = valid_mean(roi_maps[:, :, 1], axis=2)
        population, fly_count = valid_mean(np.stack((fly1, fly2), axis=2), axis=2)
        self.assertEqual((int(count1[0, 0]), int(count2[0, 0])), (2, 1))
        self.assertEqual(population[0, 0], 6.0)
        self.assertEqual(fly_count[0, 0], 2)

    def test_synthetic_center_surround_gate_and_conditional_dog(self) -> None:
        y, x = np.mgrid[:15, :15]
        radius = np.hypot(y - 7, x - 7)
        image = -np.exp(-.5 * (radius / 1.0) ** 2) + .45 * np.exp(-.5 * (radius / 4.0) ** 2)
        fly_maps = np.stack([image * scale for scale in (.9, 1., 1.1, .95, 1.05)], axis=2)
        lofo = np.stack([valid_mean(np.delete(fly_maps, i, axis=2), axis=2)[0]
                         for i in range(5)], axis=2)
        config = {"center_zone_radius_px": 1.5, "surround_zone_inner_px": 3.,
                  "surround_zone_outer_px": 6., "dog_min_same_sign_flies": 4}
        self.assertTrue(dog_gate(fly_maps, lofo, config)["descriptive_dog_gate"])
        edges = np.arange(12, dtype=float)
        profile, _ = radial_profile(image, edges)
        fit = fit_radial_dog((edges[:-1] + edges[1:]) / 2, profile)
        self.assertIsNotNone(fit)
        self.assertLess(fit["center_amplitude"], 0)
        self.assertGreater(fit["surround_amplitude"], 0)

    def test_one_fly_uses_all_eligible_payload_rows_without_split(self) -> None:
        rng = np.random.default_rng(11)
        stimulus = rng.choice([-1, 1], size=(620, 225)).astype(np.float32)
        frame_count = 600
        raw = (20 + 2 * stimulus[:frame_count, 7 * 15 + 7] +
               .2 * rng.normal(size=frame_count))[:, None].astype(np.float32)
        aligned = SimpleNamespace(
            session=SimpleNamespace(fly="fly1", run_id="synthetic"),
            stimulus=stimulus, update_index=np.arange(frame_count), response=raw,
            roi_labels=["Mean1"], imaging_time_us=np.arange(frame_count) * 70_000,
            original_sample_index=np.arange(frame_count),
            qc={"source_sha256": {"Results.csv": "synthetic"}},
        )
        config = {"temporal_bins": 4, "updates_per_bin": 10,
                  "max_raw_zero_fraction": .2, "minimum_response_std": 1e-8,
                  "gaussian_sigma_seconds": .5, "gaussian_truncate_sigma": 3.,
                  "center_uncertain_split_distance_px": 2.}
        with tempfile.TemporaryDirectory() as folder:
            summary, rows, _, _, _, _, path = _one_fly(aligned, config, Path(folder))
            with np.load(path) as saved:
                np.testing.assert_array_equal(saved["source_original_results_rows"],
                                              np.arange(39, frame_count))
                self.assertEqual(saved["full_kernel"].shape, (4, 15, 15, 1))
            self.assertEqual(summary["full_payload_frames"], frame_count)
            self.assertEqual(rows[0]["rf_frames"], frame_count - 39)


if __name__ == "__main__":
    unittest.main()
