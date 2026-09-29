"""Causal stimulus windows include current and earlier updates only."""
import unittest
import numpy as np
from dm8_modeling.features.lagged import lagged_design


class LaggedFeatureContract(unittest.TestCase):
    def test_window_and_incomplete_history(self):
        stimulus = np.arange(12, dtype=np.float32).reshape(6, 2)
        np.testing.assert_array_equal(lagged_design(stimulus, np.array([3]), 3), [[6, 7, 4, 5, 2, 3]])
        with self.assertRaises(ValueError):
            lagged_design(stimulus, np.array([1]), 3)
