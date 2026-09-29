import unittest
from pathlib import Path

import numpy as np

from dm8_modeling.data import AlignedSession, Session, verify_binary_stimulus_package
from dm8_modeling.model import causal_ema_residual, fit_sta_baseline, lagged_design
from dm8_modeling.pixel import adjust_pixel_reports, fit_pixel_model, predict_pixel_model
from dm8_modeling.ridge import binned_design, fit_binned_ridge


class LaggedDesignTests(unittest.TestCase):
    def test_binary_package_seed_and_display_mapping(self):
        recipe = {
            "stimulus_family": "binary_discrete_time",
            "randomization": {"seed": 17},
            "family_parameters": {"binary_bright_probability": 0.5},
            "rendering": {"dark_level": 0, "bright_level": 100, "color_channel": "green"},
            "geometry": {"summary": {"derived": {
                "actual_cell_width_deg": 4, "actual_cell_height_deg": 4,
            }}},
        }
        updates = np.where(np.random.RandomState(17).random_sample((3, 2, 2)) < 0.5, 1., -1.).astype(np.float32)
        gray = np.where(updates > 0, 100, 0).astype(np.uint8)
        package = {
            "stimulus_updates_rc_float32": updates,
            "stimulus_updates_display_gray_uint8": gray,
            "display_frames_gray_uint8": np.repeat(gray, 2, axis=0),
            "update_start_display_frame_idx_int32": np.array([0, 2, 4]),
        }
        qc = verify_binary_stimulus_package(recipe, package)
        self.assertTrue(qc["seed_reconstruction_passed"])
        self.assertEqual(qc["plus_one_commanded_gray"], 100)
        corrupted = dict(package, stimulus_updates_display_gray_uint8=gray.copy())
        corrupted["stimulus_updates_display_gray_uint8"][0, 0, 0] = 50
        with self.assertRaisesRegex(ValueError, "digital gray"):
            verify_binary_stimulus_package(recipe, corrupted)

    def test_current_and_past_updates_only(self):
        stimulus = np.arange(10, dtype=np.float32).reshape(5, 2)
        design = lagged_design(stimulus, np.array([2, 3]), lag_count=2)
        np.testing.assert_array_equal(design, [[4, 5, 2, 3], [6, 7, 4, 5]])

    def test_rejects_incomplete_history(self):
        with self.assertRaises(ValueError):
            lagged_design(np.ones((5, 2)), np.array([0]), lag_count=2)

    def test_synthetic_signal_is_predictable_on_later_block(self):
        rng = np.random.default_rng(10)
        stimulus = rng.choice([-1.0, 1.0], size=(1500, 225)).astype(np.float32)
        response = (stimulus[:, 12] + 0.05 * rng.normal(size=1500)).astype(np.float32)[:, None]
        session = Session(Path("/unused/fly1/run"), "fly1", "run")
        aligned = AlignedSession(
            session=session,
            stimulus=stimulus,
            update_index=np.arange(1500),
            response=response,
            roi_labels=["Mean1"],
            imaging_time_us=np.arange(1500, dtype=np.int64) * 66667,
            update_time_us=np.arange(1500, dtype=np.int64) * 66667,
            payload_end_us=1500 * 66667,
            qc={},
        )
        result = fit_sta_baseline(aligned, lag_count=2)
        self.assertGreater(result.report["roi_metrics"][0]["full_sta_test_r"], 0.7)
        self.assertEqual(result.report["purge_frames"], 2)

    def test_ema_residual_never_uses_future_values(self):
        times = np.arange(20, dtype=np.int64) * 100_000
        original = np.ones((20, 1), dtype=np.float32)
        changed_future = original.copy()
        changed_future[10:] = 100
        early_a = causal_ema_residual(original, times)
        early_b = causal_ema_residual(changed_future, times)
        np.testing.assert_array_equal(early_a[:10], early_b[:10])

    def test_binned_design_uses_disjoint_past_blocks(self):
        stimulus = np.arange(10, dtype=np.float32).reshape(10, 1)
        x = binned_design(stimulus, np.array([5]), bins=2, updates_per_bin=2)
        np.testing.assert_array_equal(x, [[4.5, 2.5]])

    def test_ridge_recovers_simple_signal_on_late_block(self):
        rng = np.random.default_rng(20)
        stimulus = rng.choice([-1.0, 1.0], size=(1500, 225)).astype(np.float32)
        response = (stimulus[:, 12] + 0.05 * rng.normal(size=1500)).astype(np.float32)[:, None]
        session = Session(Path("/unused/fly1/run"), "fly1", "run")
        aligned = AlignedSession(
            session, stimulus, np.arange(1500), response, ["Mean1"],
            np.arange(1500, dtype=np.int64) * 66667,
            np.arange(1500, dtype=np.int64) * 66667,
            1500 * 66667, {},
        )
        result = fit_binned_ridge(aligned, bins=1, updates_per_bin=1)
        self.assertGreater(result.report["roi_metrics"][0]["test_r"], 0.7)

    def test_pixel_model_recovers_location_and_lag_without_future_response_leakage(self):
        rng = np.random.default_rng(42)
        stimulus = rng.choice([-1.0, 1.0], size=(1800, 225)).astype(np.float32)
        response = (2 * stimulus[np.maximum(np.arange(1800) - 2, 0), 97]
                    + 0.5 * rng.normal(size=1800)).astype(np.float32)[:, None]
        times = np.arange(1800, dtype=np.int64) * 66667
        aligned = AlignedSession(
            Session(Path("/unused/fly1/run"), "fly1", "run"),
            stimulus, np.arange(1800), response, ["Mean1"], times, times,
            1800 * 66667, {"fly_side_orientation_calibration": "local_row_col_flip_row_col"},
        )
        result = fit_pixel_model(aligned, lag_count=5)
        entry = result.report["roi_metrics"][0]
        self.assertEqual((entry["pixel_row_zero_based"], entry["pixel_col_zero_based"]), (6, 7))
        self.assertEqual((entry["fly_side_pixel_row_zero_based"], entry["fly_side_pixel_col_zero_based"]), (8, 7))
        self.assertTrue(entry["pixel_stable_train_validation"])
        self.assertGreater(entry["test_r2"], 0.8)
        self.assertLess(entry["shift_null_p_two_sided"], 0.01)
        self.assertEqual(int(np.argmax(np.abs(result.coefficients[0]))), 2)

        future_changed = response.copy()
        future_changed[1300:] = 100 * rng.normal(size=(500, 1))
        aligned.response = future_changed
        changed = fit_pixel_model(aligned, lag_count=5)
        self.assertEqual(int(changed.selected_pixels[0]), int(result.selected_pixels[0]))
        self.assertEqual(changed.report["roi_metrics"][0]["selected_penalty"], entry["selected_penalty"])

    def test_fdr_adjusts_across_runs(self):
        reports = [
            {"roi_metrics": [{"shift_null_p_two_sided": 0.01}]},
            {"roi_metrics": [{"shift_null_p_two_sided": 0.2}]},
        ]
        adjust_pixel_reports(reports)
        self.assertAlmostEqual(reports[0]["roi_metrics"][0]["shift_null_q_all_rois"], 0.02)
        self.assertAlmostEqual(reports[1]["roi_metrics"][0]["shift_null_q_all_rois"], 0.2)

    def test_saved_pixel_coefficients_are_sufficient_for_prediction(self):
        stimulus = np.arange(24, dtype=np.float32).reshape(6, 4)
        updates = np.array([2, 3, 5])
        coefficients = np.array([[2.0, -1.0], [0.5, 0.25]])
        pixels = np.array([1, 3])
        intercepts = np.array([7.0, 10.0])
        result = predict_pixel_model(stimulus, updates, coefficients, pixels, intercepts)
        expected_first = 7 + 2 * stimulus[2, 1] - stimulus[1, 1]
        expected_second = 10 + 0.5 * stimulus[2, 3] + 0.25 * stimulus[1, 3]
        np.testing.assert_allclose(result[0], [expected_first, expected_second])
        with self.assertRaisesRegex(ValueError, "causal history"):
            predict_pixel_model(stimulus, np.array([0]), coefficients, pixels, intercepts)


if __name__ == "__main__":
    unittest.main()
