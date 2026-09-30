"""Scientific invariants for fly-specific RF and response-shift validation."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from dm8_modeling.experiments.phase63 import draw_shifts, estimate_fly, prepare_fly
from dm8_modeling.preprocessing.rf_response import li_style_relative_response
from dm8_modeling.rf.validation import cancellation, consensus, empirical_test, align_temporal_bins


class FlyValidationTests(unittest.TestCase):
    def test_cancellation_distinguishes_weak_same_sign_from_strong_mixed(self):
        self.assertEqual(float(cancellation(np.array([1e-8] * 5))), 0.)
        self.assertEqual(float(cancellation(np.array([-1., 1.]))), 1.)
        result = consensus(np.array([[[-1., 0.]], [[-2., 1.]], [[-3., 2.]], [[-4., -1.]], [[1., -2.]]]))
        self.assertEqual(result['negative_count'][0, 0], 4)
        self.assertTrue(result['sign_mixed'][0, 0])

    def test_empirical_tail_has_plus_one_and_keeps_missing_distinct(self):
        null = np.array([-2., -1., 0., 1., np.nan])
        self.assertEqual(empirical_test(-3., null)['p'], 1/5)
        self.assertEqual(empirical_test(-1., null)['p'], 3/5)
        self.assertEqual(empirical_test(2., null, 'magnitude')['p'], 1/5)
        self.assertIsNone(empirical_test(np.nan, null)['p'])

    def test_offsets_exclude_near_zero_and_preserve_recording_length(self):
        config = {'minimum_shift_seconds': 60., 'n_null': 1000}
        first = draw_shifts(8000, 75_000., config, np.random.default_rng(3))
        second = draw_shifts(8000, 75_000., config, np.random.default_rng(4))
        self.assertTrue(np.all((first >= 800) & (first <= 7200)))
        self.assertFalse(np.array_equal(first, second))

    def test_one_center_used_for_all_bins_with_no_wrap(self):
        kernel = np.zeros((4, 15, 15, 1))
        kernel[:, 0, 0, 0] = [-1., -2., 3., 4.]
        aligned = align_temporal_bins(kernel, np.array([[0., 0.]]))
        np.testing.assert_array_equal(aligned[:, 7, 7, 0], [-1., -2., 3., 4.])
        self.assertTrue(np.isnan(aligned[:, 0, 0, 0]).all())

    def test_null_reprocesses_shifted_raw_jointly_and_reestimates_centers(self):
        rng = np.random.default_rng(72)
        stimulus = rng.choice([-1., 1.], (700, 225)).astype(np.float32)
        raw = 50 + rng.normal(size=(650, 2))
        raw[:, 0] += 5 * stimulus[:650, 50]
        raw[:, 1] += 4 * stimulus[:650, 100]
        original = raw.copy()
        aligned = SimpleNamespace(response=raw, update_index=np.arange(650), stimulus=stimulus,
                                  imaging_time_us=np.arange(650) * 75_000, session=SimpleNamespace(fly='synthetic'))
        estimator = {'max_raw_zero_fraction': .2, 'minimum_response_std': 1e-8,
                     'temporal_bins': 4, 'updates_per_bin': 10,
                     'gaussian_sigma_seconds': .5, 'gaussian_truncate_sigma': 3.}
        prepared = prepare_fly(aligned, estimator)
        actual = estimate_fly(prepared, estimator)
        with patch('dm8_modeling.experiments.phase63.li_style_relative_response',
                   wraps=li_style_relative_response) as preprocess:
            null = estimate_fly(prepared, estimator, 200)
            np.testing.assert_array_equal(preprocess.call_args.args[0], np.roll(original, 200, axis=0))
        np.testing.assert_array_equal(raw, original)
        self.assertFalse(np.array_equal(actual['centers'], null['centers']))
        self.assertEqual(null['mean_bins'].shape, (4, 15, 15))


if __name__ == '__main__':
    unittest.main()
