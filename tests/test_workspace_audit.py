"""Focused contracts for workspace discovery, split leakage and candidate F0."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from dm8_modeling.data import AlignedSession, Session, _read_clock, _read_results, associate_imaging_with_updates
from dm8_modeling.pipeline import build_model_dataset
from dm8_modeling.pixel import _shift_p_values
from dm8_modeling.preprocessing import candidate_response, causal_ema_baseline
from dm8_modeling.splits import blocked_split
from dm8_modeling.workspace import WorkspacePaths, scan_data_inventory, write_inventory


class WorkspaceAuditTests(unittest.TestCase):
    def test_inventory_reads_without_changing_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            session = root / "Dm8_module" / "UV-15Hz" / "fly1" / "20260619_105040"
            session.mkdir(parents=True)
            (root / "simulate").mkdir()
            results = session / "Results.csv"
            results.write_text(" ,Mean1\n1,2\n2,3\n")
            before = results.read_bytes()
            paths = WorkspacePaths.resolve(root)
            self.assertEqual(paths.data_root, (root / "Dm8_module").resolve())
            rows = scan_data_inventory(paths.data_root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["metadata"]["row_count"], 2)
            self.assertEqual(rows[0]["file_category"], "ROI measurements")
            write_inventory(rows, root / "outputs")
            self.assertEqual(results.read_bytes(), before)

    def test_stimulus_histories_do_not_overlap_even_when_imaging_is_faster(self):
        dense_index = np.arange(600) // 4
        with self.assertRaisesRegex(ValueError, "histories overlap"):
            blocked_split(dense_index, 18, validation=True)
        normal_index = np.arange(600)
        split = blocked_split(normal_index, 18, validation=True)
        self.assertEqual(split.train.stop, 300)
        self.assertEqual(split.validation.start, 318)
        self.assertEqual(split.test.start, 438)

    def test_candidate_transforms_are_causal_and_zero_safe(self):
        values = np.array([[0., 10.], [2., 10.], [3., 11.], [4., 12.]], dtype=np.float32)
        times = np.arange(4, dtype=np.int64) * 1_000_000
        modified = values.copy()
        modified[3] = 999
        for kind in ("causal_ema_residual_60s", "candidate_ema_dff_60s"):
            a = candidate_response(values, times, kind)
            b = candidate_response(modified, times, kind)
            np.testing.assert_array_equal(a[:3], b[:3])
            self.assertTrue(np.isfinite(a).all())
        baseline = causal_ema_baseline(values, times)
        self.assertEqual(baseline.shape, values.shape)
        with self.assertRaises(ValueError):
            causal_ema_baseline(values, np.array([0, 1, 1, 2]))

    def test_malformed_results_and_clocks_fail_loudly(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            results = folder / "Results.csv"
            results.write_text(" ,Mean1\n1,2\n3,4\n")
            with self.assertRaisesRegex(ValueError, "consecutive"):
                _read_results(results)
            results.write_text(" ,Mean1,Mean1\n1,2,3\n2,3,4\n")
            with self.assertRaisesRegex(ValueError, "duplicate ROI"):
                _read_results(results)
            clock = folder / "ttl.csv"
            clock.write_text("timestamp_us\n1\n1\n")
            with self.assertRaisesRegex(ValueError, "Non-increasing"):
                _read_clock(clock, "timestamp_us")
            with self.assertRaisesRegex(ValueError, "lacks required column"):
                _read_clock(clock, "missing")
            with self.assertRaises(FileNotFoundError):
                _read_clock(folder / "missing_ttl.csv", "timestamp_us")

    def test_alignment_uses_past_update_and_excludes_end_boundary(self):
        updates = np.array([100, 200, 300])
        imaging = np.array([99, 100, 199, 200, 349, 350, 400])
        index, included = associate_imaging_with_updates(updates, imaging, 350)
        np.testing.assert_array_equal(index[included], [0, 0, 1, 2])
        np.testing.assert_array_equal(included, [False, True, True, True, True, False, False])
        with self.assertRaisesRegex(ValueError, "payload end"):
            associate_imaging_with_updates(updates, imaging, 300)

    def test_model_dataset_shape_and_late_response_independence(self):
        rng = np.random.default_rng(4)
        stimulus = rng.choice([-1., 1.], size=(650, 225)).astype(np.float32)
        response = stimulus[:, 9, None] + rng.normal(0, .05, size=(650, 1))
        time = np.arange(650, dtype=np.int64) * 66667
        aligned = AlignedSession(Session(Path("/unused/fly1/run"), "fly1", "run"), stimulus,
                                 np.arange(650), response, ["Mean1"], time, time, int(time[-1] + 1), {})
        dataset = build_model_dataset(aligned, lag_count=3)
        self.assertEqual(dataset.X.shape, (648, 675))
        self.assertEqual(dataset.y.shape, (648, 1))
        changed = response.copy()
        changed[-20:] += 100
        aligned.response = changed
        again = build_model_dataset(aligned, lag_count=3)
        np.testing.assert_array_equal(dataset.X, again.X)
        np.testing.assert_array_equal(dataset.y[:-20], again.y[:-20])

    def test_rank_one_svd_and_shift_null_sanity(self):
        temporal = np.array([1., 2., -1.])
        spatial = np.arange(1., 6.)
        rank_one = np.outer(temporal, spatial)
        s = np.linalg.svd(rank_one, compute_uv=False)
        self.assertAlmostEqual(float(s[0] ** 2 / np.sum(s ** 2)), 1.0)
        rank_two = rank_one + np.outer(np.array([0., 1., 2.]), np.array([2., -1., 0., 3., 1.]))
        s2 = np.linalg.svd(rank_two, compute_uv=False)
        self.assertLess(float(s2[0] ** 2 / np.sum(s2 ** 2)), 1.0)
        rng = np.random.default_rng(8)
        predicted = rng.normal(size=(500, 1))
        signal = predicted + rng.normal(scale=.1, size=(500, 1))
        independent = rng.normal(size=(500, 1))
        self.assertLess(float(_shift_p_values(signal, predicted, 30)[0]), .05)
        self.assertGreater(float(_shift_p_values(independent, predicted, 30)[0]), .01)


if __name__ == "__main__":
    unittest.main()
