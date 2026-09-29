"""Validation/test response changes cannot alter a train-fitted scale."""
import unittest
import numpy as np
from dm8_modeling.preprocessing.normalization import fit_response_scaler


class NormalizationContract(unittest.TestCase):
    def test_train_scale_is_fixed_and_zero_variance_marked(self):
        values = np.array([[1., 5.], [3., 5.], [100., 100.]])
        mask = np.array([True, True, False])
        scaler = fit_response_scaler(values, mask, "train_zscore")
        np.testing.assert_array_equal(scaler.mean, [2., 5.])
        np.testing.assert_array_equal(scaler.scale, [1., 1.])
        np.testing.assert_array_equal(scaler.zero_variance_roi, [False, True])
        values[-1] *= 100
        later = fit_response_scaler(values, mask, "train_zscore")
        np.testing.assert_array_equal(later.mean, scaler.mean)
