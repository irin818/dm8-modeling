import unittest
from pathlib import Path

import numpy as np

from dm8_modeling.data import AlignedSession, Session
from dm8_modeling.model import causal_ema_residual, fit_sta_baseline, lagged_design
from dm8_modeling.ridge import binned_design, fit_binned_ridge


class LaggedDesignTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
