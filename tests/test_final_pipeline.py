"""Synthetic scientific invariants and optional local frozen-data integrity checks."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from dm8_modeling.alignment import estimate_centers, subpixel_align, fit_axis_centers
from dm8_modeling.data import Recording, source_manifest, technical_roi_mask
from dm8_modeling.population import valid_mean, fly_spatial, population_spatial
from dm8_modeling.preprocessing import relative_response
from dm8_modeling.rf import native_design, reverse_correlation, rf_zscore, estimate_strf, global_energy_lag
from dm8_modeling.statistics import circular_shifts, empirical_p
from dm8_modeling.timing import associate_frames, read_clock

# Resolve the repository without relying on a working-directory convention.
ROOT = next(p for p in Path(__file__).resolve().parents if (p/"configs/final_analysis.json").is_file())
CONFIG = json.loads((ROOT/"configs/final_analysis.json").read_text())


class FinalPipelineTests(unittest.TestCase):
    """Verify mathematical assumptions with known signals, not historical helpers."""

    def test_no_future_stimulus_leakage(self):
        """Frames between TTL edges must use the previous, never next update."""
        indices, payload = associate_frames(np.array([10,20,30]), np.array([5,10,19,20,29,30,40]), 40)
        np.testing.assert_array_equal(indices, [-1,0,0,1,1,2,2])
        np.testing.assert_array_equal(payload, [False,True,True,True,True,True,False])

    def test_clock_rejects_duplicates(self):
        """A duplicate TTL would make frame ownership ambiguous and must fail."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"clock.csv"
            path.write_text("timestamp_us\n10\n10\n20\n")
            with self.assertRaises(ValueError):
                read_clock(path, "timestamp_us")

    def test_lag_indexing(self):
        """lag0=current and lag2=current−2 preserve pixel order."""
        stimulus = np.arange(20, dtype=float).reshape(10,2)
        design = native_design(stimulus, np.array([4,7]), 3)
        np.testing.assert_array_equal(design, [[8,9,6,7,4,5],[14,15,12,13,10,11]])
        with self.assertRaises(ValueError):
            native_design(stimulus, np.array([1]), 3)

    def test_gaussian_preprocessing(self):
        """Constant fluorescence is removed; an impulse leaves a signed Gaussian baseline."""
        config = {**CONFIG, "gaussian_sigma_seconds": 2.0}
        times = np.arange(101)*1_000_000
        signal = np.full((101,1), 100.0)
        response, margin = relative_response(signal, times, config)
        np.testing.assert_allclose(response, 0, atol=1e-10)
        signal[50] += 10
        response, margin = relative_response(signal, times, config)
        offsets = np.arange(-6,7)
        weights = np.exp(-.5*(offsets/2)**2)
        weights /= weights.sum()
        expected = -10*weights
        expected[6] += 10
        np.testing.assert_allclose(response[44:57,0], expected, atol=1e-6)
        self.assertEqual(margin, 6)

    def test_irregular_gaussian_clock_rejected(self):
        """The frame-based Gaussian approximation must reject a large timing gap."""
        times = np.arange(1000)*100_000
        times[500:] += 100_000
        with self.assertRaises(ValueError):
            relative_response(np.ones((1000,1)), times, CONFIG)

    def test_primary_edge_trim(self):
        """Primary covariance excludes both 3σ edges; full-record lag selection keeps them."""
        rng = np.random.default_rng(8)
        stimulus = rng.choice([-1.,1.], size=(1100,225)).astype(np.float32)
        response = (100+np.sin(np.arange(1001)/7))[:,None].astype(np.float32)
        recording = Recording("synthetic", "edge-test", stimulus, response,
                              np.arange(1001), np.arange(1001)*100_000, np.array([0]), {})
        full = estimate_strf(recording, CONFIG, trim=False)
        primary = estimate_strf(recording, CONFIG, trim=True)
        self.assertEqual(primary["margin"], 300)
        self.assertEqual(full["frames"], 1001-39)
        self.assertEqual(primary["frames"], 1001-600)
        self.assertEqual(primary["kernel"].shape, (40,15,15,1))

    def test_reverse_correlation_shape_sign(self):
        """Balanced ON stimulation coupled to lower response gives negative covariance."""
        stimulus = np.array([[-1.],[1.],[-1.],[1.]])
        response = np.column_stack((-2*stimulus[:,0]+100, 3*stimulus[:,0]+20))
        kernel = reverse_correlation(stimulus, response)
        self.assertEqual(kernel.shape, (1,2))
        np.testing.assert_allclose(kernel, [[-2,3]])

    def test_strf_zscore(self):
        """Whole-STRF normalization is ROI-specific and does not amplify constants."""
        normalized = rf_zscore(np.column_stack((np.arange(20), np.arange(20)*10, np.ones(20))))
        np.testing.assert_allclose(normalized[:,:2].mean(axis=0), 0, atol=1e-12)
        np.testing.assert_allclose(normalized[:,:2].std(axis=0), 1)
        np.testing.assert_array_equal(normalized[:,2], np.zeros(20))

    def test_gaussian_center_estimation(self):
        """A known negative Gaussian recovers its fractional center, independent of sign."""
        rows, cols = np.mgrid[:15,:15]
        image = -np.exp(-((rows-6.25)**2+(cols-8.5)**2)/(2*1.5**2))
        np.testing.assert_allclose(estimate_centers(image[:,:,None], CONFIG), [[6.25,8.5]], atol=.25)
        np.testing.assert_allclose(estimate_centers(-image[:,:,None], CONFIG), [[6.25,8.5]], atol=.25)

    def test_center_quality_rejection(self):
        """Flat RFs have no center; a strict fit-quality threshold rejects a two-peak profile."""
        self.assertTrue(np.isnan(estimate_centers(np.ones((15,15,1)), CONFIG)).all())
        profile = np.zeros((1,15))
        profile[0,[2,12]] = 1
        strict = {**CONFIG, "center_fit_quality_min": .999}
        self.assertTrue(np.isnan(fit_axis_centers(profile, strict)).all())

    def test_roi_to_fly_mean(self):
        """Centered ROI maps are averaged equally within the fly and retain contributor counts."""
        row, col = np.mgrid[:15,:15]
        image = -np.exp(-((row-7)**2+(col-7)**2)/(2*1.5**2))
        kernel = np.stack([image, 3*image], axis=2)[None]
        fly = fly_spatial({"kernel": kernel}, 0, CONFIG)
        np.testing.assert_allclose(fly["map"], 2*image, atol=1e-12)
        np.testing.assert_array_equal(fly["roi_support"], np.full((15,15),2))

    def test_global_energy_uses_equal_fly_weights(self):
        """One fly with 100 ROI must not outweigh one with one ROI in lag selection."""
        first = np.zeros((40,15,15,1))
        second = np.zeros((40,15,15,100))
        first[1,7,7,:] = 10
        second[2,7,7,:] = 2
        self.assertEqual(global_energy_lag([{"kernel":first},{"kernel":second}]), 1)

    def test_subpixel_no_wrap(self):
        """Fractional translations preserve interpolation and leave the lost boundary NaN."""
        image = np.arange(15, dtype=float)[None,:,None]*np.ones((15,1,1))
        aligned, support = subpixel_align(image, np.array([[7.,6.5]]))
        self.assertTrue(np.isnan(aligned[:,0,:]).all())
        self.assertFalse(support[:,0,:].any())
        np.testing.assert_allclose(aligned[:,1:,0], image[:,1:,0]-.5)

    def test_nan_not_zero(self):
        """Absent contributors change the denominator, not the signal."""
        mean, count = valid_mean(np.array([[np.nan,4],[2,6],[np.nan,np.nan]]), 0)
        np.testing.assert_array_equal(mean, [2,5])
        np.testing.assert_array_equal(count, [1,2])
        missing, count = valid_mean(np.full((2,3), np.nan), 0)
        self.assertTrue(np.isnan(missing).all())

    def test_equal_fly_weighting(self):
        """Animals contribute equally despite very different ROI counts."""
        flies = [{"map":np.full((15,15), value), "roi_support":np.full((15,15), count)}
                 for value,count in ((-2.,1),(0.,100))]
        population = population_spatial(flies)
        np.testing.assert_array_equal(population["map"], np.full((15,15), -1))
        np.testing.assert_array_equal(population["roi_support"], np.full((15,15), 101))

    def test_temporal_lag_recovery(self):
        """A delayed synthetic response peaks at its known past-stimulus lag."""
        rng = np.random.default_rng(31)
        stimulus = rng.choice([-1.,1.], size=(20000,1))
        indices = np.arange(10,len(stimulus))
        design = native_design(stimulus, indices, 8)
        response = -3*stimulus[indices-4]
        kernel = reverse_correlation(design, response)
        self.assertEqual(int(np.argmax(np.abs(kernel[:,0]))), 4)
        self.assertLess(kernel[4,0], -2.99)


    def test_circular_shift_minimum_distance(self):
        """Null shifts stay ≥60s away in both circular directions."""
        shifts = circular_shifts(9000, 100_000., CONFIG, np.random.default_rng(9))
        self.assertGreaterEqual(int(shifts.min()), 600)
        self.assertGreaterEqual(int((9000-shifts).min()), 600)
        self.assertEqual(len(shifts), 500)
        self.assertEqual(empirical_p(-10, np.array([-2,0,2])), .25)
        self.assertEqual(empirical_p(0, np.array([-2,0,2]), positive=True), .75)

    def test_technical_qc(self):
        """Exclude constants, nonfinite and zero-heavy ROI without RF-sign selection."""
        response = np.column_stack((np.arange(100)+1, np.ones(100), np.zeros(100), np.arange(100)+1.)).astype(float)
        response[0,3] = np.nan
        np.testing.assert_array_equal(technical_roi_mask(response, CONFIG), [True,False,False,False])

    def test_source_data_immutable(self):
        """Local full integration check: every protected source matches retained hashes."""
        roots = {name:ROOT/name for name in CONFIG["protected_source_roots"]}
        if not all(path.is_dir() for path in roots.values()):
            self.skipTest("Protected experimental inputs are local and not distributed by Git")
        expected = json.loads((ROOT/"results/source_hashes.json").read_text())
        self.assertEqual(source_manifest(roots), expected)

    def test_final_numerical_regression(self):
        """Retained final results must match all frozen-data targets and source/config hashes."""
        from dm8_modeling.data import sha256
        summary = json.loads((ROOT/"results/final_results.json").read_text())
        self.assertEqual(summary["config_sha256"], sha256(ROOT/"configs/final_analysis.json"))
        self.assertEqual(len(summary["numerical_regression"]), 8)
        self.assertNotIn("models", summary)
        self.assertTrue(all(check["passed"] for check in summary["numerical_regression"].values()))
        for key, target in CONFIG["numerical_regression"].items():
            if key != "absolute_tolerance":
                self.assertAlmostEqual(summary["numerical_regression"][key]["actual"], target, delta=1e-6)
        self.assertTrue(summary["source_integrity"]["unchanged"])
        self.assertEqual(summary["source_integrity"]["sha256_before"], summary["source_integrity"]["sha256_after"])
        samples = np.asarray(summary["statistics"]["samples"])
        self.assertEqual(samples.shape, (500,2))
        self.assertEqual(empirical_p(summary["spatial"]["spatial_center"], samples[:,0]),
                         summary["statistics"]["center_p_negative"])
        self.assertEqual(empirical_p(summary["spatial"]["spatial_surround"], samples[:,1], positive=True),
                         summary["statistics"]["surround_p_positive"])

    def test_rf_figure_shared_scale(self):
        """Every RF panel preserves its array and shares one symmetric quantitative color scale."""
        from dm8_modeling import plotting
        flies = []
        for index in range(5):
            image = np.zeros((15,15))
            image[7,7] = -index-1
            flies.append({"map":image})
        population = {"map":np.mean([f["map"] for f in flies], axis=0)}
        with patch.object(plotting, "save_figure") as save:
            plotting.receptive_field_figure(Path("unused"), flies, population)
        figure = save.call_args.args[0]
        try:
            norm = figure.axes[0].images[0].norm
            self.assertEqual((norm.vmin,norm.vcenter,norm.vmax), (-5,0,5))
            for axis, image in zip(figure.axes[:6], [f["map"] for f in flies]+[population["map"]], strict=True):
                self.assertIs(axis.images[0].norm, norm)
                self.assertEqual(axis.get_box_aspect(), 1)
                np.testing.assert_array_equal(axis.images[0].get_array(), image)
        finally:
            plotting.plt.close(figure)

    def test_zone_figure_keeps_negative_surround(self):
        """Separate scatter scales show every biological replicate, including negative periphery."""
        from dm8_modeling import plotting
        row, col = np.mgrid[:15,:15]
        radius = np.hypot(row-7,col-7)
        flies = []
        surround = [.005,.001,.017,-.028,.002]
        for index, value in enumerate(surround):
            image = np.zeros((15,15))
            image[radius <= 1.5] = -.7-index*.2
            image[(radius >= 3)&(radius <= 6)] = value
            flies.append({"map":image})
        population = {"map":np.mean([f["map"] for f in flies], axis=0)}
        with patch.object(plotting, "save_figure") as save:
            plotting.spatial_zone_figure(Path("unused"), flies, population, CONFIG)
        figure = save.call_args.args[0]
        try:
            values = [float(mark.get_offsets()[0,1]) for mark in figure.axes[1].collections]
            np.testing.assert_allclose(values[:5], surround, atol=1e-12)
            np.testing.assert_allclose(values[-1], np.mean(surround), atol=1e-12)
            low, high = figure.axes[1].get_ylim()
            self.assertLess(low, min(surround))
            self.assertGreater(high, max(surround))
            self.assertGreater(np.ptp(figure.axes[0].get_ylim()), 10*np.ptp(figure.axes[1].get_ylim()))
        finally:
            plotting.plt.close(figure)

    def test_final_figure_exports(self):
        """Exactly six PNG/SVG pairs remain; all PNGs retain ≥300 dpi export metadata."""
        from PIL import Image
        import xml.etree.ElementTree as ET
        expected = {"figure_1_receptive_fields", "figure_2_spatial_zones", "figure_3_temporal_rf",
                    "figure_4_full_pipeline_null", "supplementary_s1_support", "methods_pipeline"}
        folder = ROOT/"results/figures"
        self.assertEqual({p.stem for p in folder.glob("*.png")}, expected)
        self.assertEqual({p.stem for p in folder.glob("*.svg")}, expected)
        for stem in expected:
            with Image.open(folder/f"{stem}.png") as image:
                self.assertGreaterEqual(min(image.info["dpi"]), 299.9)
                self.assertEqual(image.width, 2010)
            self.assertTrue(ET.parse(folder/f"{stem}.svg").getroot().tag.endswith("svg"))
            self.assertTrue(all(line == line.rstrip() for line in (folder/f"{stem}.svg").read_text().splitlines()))
        from dm8_modeling import plotting
        with tempfile.TemporaryDirectory() as temporary:
            figure, axis = plotting.plt.subplots(figsize=(1,1))
            axis.plot([0,1],[0,1])
            plotting.save_figure(figure, Path(temporary), "export")
            vector = Path(temporary)/"export.svg"
            self.assertTrue(all(line == line.rstrip() for line in vector.read_text().splitlines()))
            self.assertTrue(ET.parse(vector).getroot().tag.endswith("svg"))


if __name__ == "__main__":
    unittest.main()
