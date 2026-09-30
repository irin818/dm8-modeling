"""Focused controls for Phase 6.1b causal lags, TRAIN scope, and audit families."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from dm8_modeling.features.lagged import lagged_design
from dm8_modeling.features.temporal_basis import binned_design
from dm8_modeling.experiments.rf_method_audit import audit_localizers, learning_rows
from dm8_modeling.rf.characterization import fdr_q_values, reverse_correlation


class RFMethodAuditTests(unittest.TestCase):
    def test_fine_lags_use_current_and_past_only(self) -> None:
        stimulus = np.arange(80 * 225).reshape(80, 225)
        rows = np.array([39, 50])
        actual = lagged_design(stimulus, rows, 40).reshape(2, 40, 225)
        np.testing.assert_array_equal(actual[0, 0], stimulus[39])
        np.testing.assert_array_equal(actual[0, -1], stimulus[0])
        changed = stimulus.copy()
        changed[51:] *= -1
        np.testing.assert_array_equal(actual, lagged_design(changed, rows, 40).reshape(2, 40, 225))

    def test_synthetic_fine_lag_recovery_and_coarse_sensitivity(self) -> None:
        rng = np.random.default_rng(25)
        stimulus = rng.choice([-1, 1], size=(2400, 225)).astype(np.float32)
        updates = np.arange(39, 2400)
        x = lagged_design(stimulus, updates, 40)
        y = (stimulus[updates - 3, 72] - stimulus[updates - 4, 72])[:, None]
        fine = reverse_correlation(x, y)
        self.assertEqual(int(np.argmax(np.abs(fine[:, 0]))), 3 * 225 + 72)
        coarse = binned_design(stimulus, updates, 4, 10)
        np.testing.assert_allclose(coarse[:, :225], x.reshape(len(x), 40, 225)[:, :10].mean(axis=1))
        self.assertLess(np.max(np.abs(reverse_correlation(coarse, y))),
                        np.max(np.abs(fine)))

    def test_learning_rows_are_nested_train_only(self) -> None:
        first = np.arange(100, 140)
        second = np.arange(200, 240)
        modulo = learning_rows(first, second)
        for n in (1, 2, 3, 4):
            chosen = first[modulo < n]
            self.assertTrue(np.all(chosen < 140))
            self.assertEqual(len(chosen), n * 10)
        self.assertEqual(len(second), 40)

    def test_localizer_search_is_read_only_and_separates_code_from_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "simulate" / "moving_bar_profile.py"
            code.parent.mkdir()
            code.write_text("moving_bar_screening = True\n")
            raw = root / "Dm8_module" / "stim_recipe.json"
            raw.parent.mkdir()
            raw.write_text('{"stimulus_family": "binary_discrete_time"}')
            before = {path: path.read_bytes() for path in (code, raw)}
            result = audit_localizers(root)
            self.assertEqual(result["recorded_candidate_count"], 0)
            self.assertTrue(any(row["source_area"] == "simulate" for row in result["candidates"]))
            self.assertEqual(before, {path: path.read_bytes() for path in (code, raw)})
            own_output = root / "outputs/phase_06/rf_method_audit/summary.json"
            own_output.parent.mkdir(parents=True)
            own_output.write_text('{"moving_bar": "self-reference"}')
            self.assertEqual(audit_localizers(root)["files_scanned"]["outputs"], 0)

    def test_bh_family_changes_without_changing_p_values(self) -> None:
        p = np.array([.01, .02, 1., 1.])
        self.assertAlmostEqual(fdr_q_values(p)[0], .04)
        self.assertAlmostEqual(fdr_q_values(p[:2])[0], .02)
        np.testing.assert_array_equal(p, [.01, .02, 1., 1.])


if __name__ == "__main__":
    unittest.main()
