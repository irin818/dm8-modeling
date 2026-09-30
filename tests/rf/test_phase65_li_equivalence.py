"""Numerical invariants for the frozen Li-method sensitivity audit."""

import unittest
import csv
import json
from pathlib import Path
import numpy as np

from dm8_modeling.rf.characterization import reverse_correlation
from dm8_modeling.rf.dog import projection_matrix
from dm8_modeling.rf.li_equivalence import (aggregate, align_spatial, coarse_from_native,
    li_relative_dog, native_design, rf_zscore)

ROOT = Path(__file__).resolve().parents[2]

class Phase65Tests(unittest.TestCase):
    def test_native_lag_direction_and_no_future(self):
        stimulus = np.arange(8, dtype=np.float32)[:, None]
        x = native_design(stimulus, np.array([2, 3]), 3)
        np.testing.assert_array_equal(x, [[2, 1, 0], [3, 2, 1]])
        with self.assertRaises(ValueError):
            native_design(stimulus, np.array([1]), 3)
        with self.assertRaises(ValueError):
            native_design(stimulus, np.array([8]), 3)

    def test_peak_lag_recovered(self):
        rng = np.random.default_rng(65)
        stimulus = rng.choice([-1., 1.], size=(1500, 2)).astype(np.float32)
        updates = np.arange(5, 1500)
        x = native_design(stimulus, updates, 5)
        response = x[:, 2*2:2*2+1] + .05*rng.normal(size=(len(x), 1))
        k = reverse_correlation(x, response).reshape(5, 2)
        self.assertEqual(int(np.argmax(np.sum(k*k, axis=1))), 2)

    def test_coarse_is_mean_of_native_coefficients(self):
        rng = np.random.default_rng(651)
        stimulus = rng.choice([-1., 1.], size=(100, 3)).astype(np.float32)
        updates = np.arange(19, 100)
        x = native_design(stimulus, updates, 20)
        response = rng.normal(size=(len(x), 2))
        native = reverse_correlation(x, response).reshape(20, 1, 3, 2)
        coarse = coarse_from_native(native, 10).reshape(6, 2)
        binned = np.concatenate((x[:, :30].reshape(len(x), 10, 3).mean(axis=1),
                                 x[:, 30:].reshape(len(x), 10, 3).mean(axis=1)), axis=1)
        np.testing.assert_allclose(coarse, reverse_correlation(binned, response), atol=1e-7)

    def test_rf_zscore_whole_strf_and_roi_weighting(self):
        k = np.array([[1., 10.], [2., 20.], [3., 30.], [4., 40.]])
        z = rf_zscore(k)
        np.testing.assert_allclose(z.mean(axis=0), 0, atol=1e-12)
        np.testing.assert_allclose(z.std(axis=0), 1, atol=1e-12)
        # Response scaling cancels in each ROI's post-RF zscore, not in a raw population mean.
        np.testing.assert_allclose(rf_zscore(k*np.array([2, 5])), z)
        self.assertFalse(np.allclose(k.mean(axis=1), z.mean(axis=1)))

    def test_response_pre_zscore_and_rf_post_zscore_not_same_population_weight(self):
        rng = np.random.default_rng(20265)
        x = rng.normal(size=(1000, 3))
        y = np.column_stack((x[:, 0]+.1*rng.normal(size=1000),
                             8*x[:, 1]+.1*rng.normal(size=1000)))
        pre = reverse_correlation(x, (y-y.mean(0))/y.std(0))
        post = rf_zscore(reverse_correlation(x, y))
        self.assertFalse(np.allclose(pre.mean(axis=1), post.mean(axis=1)))
        self.assertTrue(np.allclose(post.std(axis=0), 1))

    def test_transient_surround_attenuated_by_coarse_mean(self):
        kernel = np.zeros((40, 15, 15, 1))
        kernel[:, 7, 7, 0] = -1
        kernel[2, 7, 11, 0] = 1
        self.assertEqual(kernel[2, 7, 11, 0], 1)
        self.assertAlmostEqual(coarse_from_native(kernel)[0, 7, 11, 0], .1)

    def test_subpixel_and_nan_boundary(self):
        image = np.full((15, 15, 1), np.nan)
        image[4:11, 4:11, 0] = 1
        image[7, 7, 0] = 5
        shifted, support = align_spatial(image, np.array([[7.5, 7.5]]), "bilinear")
        self.assertTrue(np.isnan(shifted[0, 0, 0]))
        self.assertFalse(support[0, 0, 0])
        self.assertGreater(shifted[7, 7, 0], 1)
        self.assertLess(shifted[7, 7, 0], 5)

    def test_weighting(self):
        fly1 = np.ones((15, 15, 2))
        fly2 = np.full((15, 15, 1), 4.)
        roi = aggregate([fly1, fly2], "roi_equal")[0]
        fly = aggregate([fly1, fly2], "fly_equal")[0]
        self.assertAlmostEqual(roi[7, 7], 2)
        self.assertAlmostEqual(fly[7, 7], 2.5)

    def test_nan_is_not_zero_in_population_mean(self):
        first = np.full((15,15,1), np.nan)
        first[7,7,0] = 2
        second = np.full((15,15,1), 4.)
        mean, roi_count, fly_count = aggregate([first, second], "fly_equal")
        self.assertAlmostEqual(mean[0,0], 4)
        self.assertEqual(roi_count[0,0], 1)
        self.assertEqual(fly_count[0,0], 1)

    def test_timing_offsets_are_fixed_and_history_checked(self):
        stimulus = np.arange(100, dtype=np.float32)[:, None]
        base = np.array([40,41,42])
        for offset in (-1,0,1):
            design = native_design(stimulus, base+offset, 40)
            self.assertTrue(np.all(design[:,1] == base+offset-1))
        with self.assertRaises(ValueError):
            native_design(stimulus, np.array([39])-1, 40)

    def test_final_null_numeric_regression(self):
        path = ROOT/"docs/phase6_5_results/final_null_results.csv"
        if not path.exists():
            self.skipTest("Full-data outputs not present in this checkout")
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        summary = json.loads((path.parent/"final_null_summary.json").read_text())
        self.assertEqual(len(rows), 500)
        observed = summary["observed_center"]
        expected = (1+sum(float(row["center"])<=observed for row in rows))/501
        self.assertAlmostEqual(summary["p_negative_center"], expected)
        self.assertLess(summary["p_negative_center"], .01)

    def test_rotation_and_li_dog(self):
        p = projection_matrix(15, 1000)
        rr, cc = np.mgrid[:15, :15]
        image = np.exp(-((rr-7)**2+(cc-7)**2)/(2*2.**2))
        profile = p @ image.ravel()
        self.assertAlmostEqual(profile[0], profile[-1], delta=.02)
        self.assertGreater(profile[7], profile[0])
        x = np.arange(-7, 8)
        y = .01-.06*(np.exp(-x*x/(2*1.5**2))-.5*np.exp(-x*x/(2*4.**2)))
        fit = li_relative_dog(x, y, (.5, 4), (1, 15), 2)
        self.assertAlmostEqual(fit["center_sigma_px"], 1.5, delta=.2)
        self.assertAlmostEqual(fit["surround_sigma_px"], 4, delta=.3)
        self.assertAlmostEqual(fit["relative_surround_amplitude"], .5, delta=.1)


if __name__ == "__main__":
    unittest.main()
