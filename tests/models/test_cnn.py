"""Checks for the saved CNN path and the held-out response boundary."""

import unittest
from pathlib import Path

import numpy as np

from dm8_modeling.cnn import fit_compact_cnn, predict_compact_cnn
from dm8_modeling.data import AlignedSession, Session
from dm8_modeling.pixel import fit_pixel_model


class CompactCNNTests(unittest.TestCase):
    def test_replay_and_test_response_do_not_change_training(self):
        rng = np.random.default_rng(89)
        stimulus = rng.choice([-1.0, 1.0], size=(620, 225)).astype(np.float32)
        response = (3 + 1.5 * stimulus[:, 63] + 0.1 * rng.normal(size=620)).astype(np.float32)[:, None]
        times = np.arange(620, dtype=np.int64) * 66667
        aligned = AlignedSession(
            Session(Path("/unused/fly1/run"), "fly1", "run"), stimulus,
            np.arange(620), response, ["Mean1"], times, times,
            620 * 66667, {},
        )
        baseline = fit_pixel_model(aligned, lag_count=3)
        saved = {
            "roi_labels": np.asarray(aligned.roi_labels),
            "selected_pixels": baseline.selected_pixels,
            "coefficients": baseline.coefficients,
            "intercepts": baseline.intercepts,
            "test_actual": baseline.test_actual,
            "test_predicted": baseline.test_predicted,
        }
        result = fit_compact_cnn(aligned, baseline.report, saved, max_epochs=2, patience=2, batch_size=128)
        first_test = baseline.report["eligible_frames"] - baseline.report["test_frames"]
        eligible_indices = aligned.update_index[aligned.update_index >= 2]
        replay = predict_compact_cnn(
            stimulus, eligible_indices[first_test:], result.model_state,
            baseline.selected_pixels, result.report["fit_mean"], result.report["fit_sd"],
        )
        np.testing.assert_allclose(replay, result.test_predicted, atol=1e-5, rtol=1e-5)
        self.assertEqual(len(result.test_predicted), baseline.report["test_frames"])

        altered = response.copy()
        altered[first_test + 2:] += 20
        aligned.response = altered
        # Eligible frame zero starts at original frame two.
        changed_saved = dict(saved, test_actual=altered[2:][first_test:])
        changed = fit_compact_cnn(aligned, baseline.report, changed_saved, max_epochs=2, patience=2, batch_size=128)
        self.assertEqual(result.report["selected_epoch"], changed.report["selected_epoch"])
        for key in result.model_state:
            np.testing.assert_array_equal(result.model_state[key], changed.model_state[key])
        np.testing.assert_allclose(result.test_predicted, changed.test_predicted, atol=1e-6, rtol=1e-6)


if __name__ == "__main__":
    unittest.main()
