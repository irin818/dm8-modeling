"""Per-ROI evaluation uses the later block and flags constant targets."""
import unittest
import numpy as np
from dm8_modeling.evaluation.metrics import score_columns


class MetricContract(unittest.TestCase):
    def test_perfect_and_constant_test_targets(self):
        actual = np.array([[0., 2.], [1., 2.], [2., 2.]])
        scores = score_columns(actual, actual.copy(), np.array([1., 1.]))
        self.assertAlmostEqual(scores["r2"][0], 1.)
        self.assertTrue(np.isnan(scores["r2"][1]))
