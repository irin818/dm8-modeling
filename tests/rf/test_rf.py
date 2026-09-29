"""ROI shift-null inference keeps the saved historical adjustment behavior."""
import unittest
import numpy as np
from dm8_modeling.rf.null_tests import _bh_q_values
from dm8_modeling.rf.sta import estimate_reverse_correlation


class RFNullContract(unittest.TestCase):
    def test_reverse_correlation_centers_training_rows(self):
        design = np.array([[0., 2.], [1., 2.], [2., 2.]])
        response = np.array([[1.], [3.], [5.]])
        np.testing.assert_allclose(
            estimate_reverse_correlation(design, response), [[4. / 3], [0.]])

    def test_bh_adjustment_is_monotone_and_bounded(self):
        q = _bh_q_values(np.array([0.001, 0.02, 0.5]))
        self.assertTrue(np.all(np.diff(q) >= 0))
        self.assertTrue(np.all((q >= 0) & (q <= 1)))
