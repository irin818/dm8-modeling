"""Focused synthetic controls for Phase 6.1 RF inference and leakage."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from dm8_modeling.datasets.splits import TEST, TRAIN
from dm8_modeling.experiments.phase6 import (_provenance, _responses, _train_halves,
                                             _representation_scores)
from dm8_modeling.preprocessing.fluorescence import candidate_response
from dm8_modeling.preprocessing.rf_response import li_style_relative_response
from dm8_modeling.rf.characterization import (
    align_kernels, characterize_halves, classify_rf, fdr_q_values,
    pairwise_spatial_similarity, rf_maps,
    reverse_correlation,
)


def _gaussian_kernel(row: float, col: float) -> np.ndarray:
    y, x = np.mgrid[:15, :15]
    image = -np.exp(-0.5 * (((y - row) / 1.5) ** 2 + ((x - col) / 2) ** 2))
    kernel = np.zeros((4, 15, 15, 1), dtype=float)
    kernel[0, :, :, 0] = image
    return kernel


class Phase6ResponseTests(unittest.TestCase):
    def test_raw_anchor_unchanged_and_li_reproducible(self) -> None:
        time = np.arange(300, dtype=np.int64) * 100_000
        raw = (10 + np.sin(np.arange(300)[:, None] / 8)).astype(np.float32)
        before = raw.copy()
        first, margin = li_style_relative_response(raw, time, sigma_seconds=1)
        second, again = li_style_relative_response(raw, time, sigma_seconds=1)
        self.assertTrue(np.array_equal(raw, before))
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(margin, again)
        identity = candidate_response(raw, time, "raw")
        self.assertTrue(np.array_equal(identity, raw))
        self.assertFalse(np.shares_memory(identity, raw))

    def test_causal_transforms_ignore_future(self) -> None:
        time = np.arange(300, dtype=np.int64) * 100_000
        raw = (10 + np.sin(np.arange(300)[:, None] / 8)).astype(np.float32)
        changed = raw.copy()
        changed[220:] += 10_000
        for kind in ("raw", "causal_ema_residual_60s", "causal_block_median_residual_60s"):
            with self.subTest(kind=kind):
                actual = candidate_response(raw, time, kind)
                altered = candidate_response(changed, time, kind)
                np.testing.assert_array_equal(actual[:220], altered[:220])

    def test_train_halves_and_preprocessing_ignore_test(self) -> None:
        frames = 2400
        time = np.arange(frames, dtype=np.int64) * 100_000
        raw = (10 + np.sin(np.arange(frames)[:, None] / 20)).astype(np.float32)
        labels = np.full(frames - 39, TEST, dtype=np.uint8)
        labels[:1600] = TRAIN

        def item(values: np.ndarray) -> SimpleNamespace:
            return SimpleNamespace(
                aligned=SimpleNamespace(response=values, imaging_time_us=time,
                                        update_index=np.arange(frames)),
                feature_definition=SimpleNamespace(history_updates=40),
                split_label=labels, update_index=np.arange(39, frames),
            )

        config = {"train_half_gap_updates_each_side": 40,
                  "li_gaussian_sigma_seconds": .5, "li_edge_truncate_sigma": 3}
        first = item(raw)
        rows = _train_halves(first, config)
        values = _responses(first, *rows)
        changed = raw.copy()
        changed[1800:] += 1000
        altered = item(changed)
        new_rows = _train_halves(altered, config)
        compared = _responses(altered, *new_rows)
        for kind in values:
            for original, edited in zip(values[kind], compared[kind], strict=True):
                np.testing.assert_array_equal(original, edited)
        np.testing.assert_array_equal(rows[0], new_rows[0])
        np.testing.assert_array_equal(rows[1], new_rows[1])
        self.assertLess(np.max(rows[1]), 1600)
        rng = np.random.default_rng(4)
        x_first = rng.normal(size=(len(rows[0]), 900))
        x_second = rng.normal(size=(len(rows[1]), 900))
        original_rf = characterize_halves(x_first, values["raw"][0], x_second,
                                          values["raw"][1], 4, 10)
        altered_rf = characterize_halves(x_first, compared["raw"][0], x_second,
                                         compared["raw"][1], 4, 10)
        np.testing.assert_array_equal(original_rf["shift_null_p"], altered_rf["shift_null_p"])

    def test_response_provenance_declares_raw_anchor_and_causality(self) -> None:
        fake = SimpleNamespace(
            fly_id="fly1", run_id="run1", original_sample_index=np.arange(10),
            aligned=SimpleNamespace(session=SimpleNamespace(path=Path("/raw/run1")),
                                    qc={"source_sha256": {"Results.csv": "abc123"}}),
        )
        config = {"train_fold": "fold_a", "li_gaussian_sigma_seconds": 10,
                  "li_edge_truncate_sigma": 3}
        record = _provenance(fake, config, np.array([1, 2]), np.array([7, 8]))
        self.assertEqual(record["source_raw_sha256"], "abc123")
        self.assertEqual(record["first_original_results_rows"], [1, 2])
        transforms = {row["name"]: row for row in record["transformations"]}
        self.assertFalse(transforms["li_style_rf_relative"]["causal"])
        self.assertTrue(transforms["causal_ema_residual_60s"]["causal"])
        self.assertIn("OFFLINE RF", transforms["li_style_rf_relative"]["scientific_purpose"])


class Phase6RFTests(unittest.TestCase):
    def test_rf_shape_and_train_half_projection(self) -> None:
        rng = np.random.default_rng(3)
        x = rng.normal(size=(600, 900))
        true_kernel = np.zeros((900, 2))
        true_kernel[100, 0] = 1
        true_kernel[380, 1] = -1
        y = x @ true_kernel + .1 * rng.normal(size=(600, 2))
        result = characterize_halves(x[:300], y[:300], x[300:], y[300:], 4, 30)
        self.assertEqual(result["kernel_first"].shape, (900, 2))
        self.assertEqual(result["spatial"].shape, (15, 15, 2))
        self.assertEqual(result["temporal"].shape, (4, 2))
        self.assertTrue(np.all(result["train_projection_r"] > .5))
        self.assertEqual(reverse_correlation(x[:300], y[:300]).shape, (900, 2))

    def test_shift_null_and_bh_fdr(self) -> None:
        q = fdr_q_values(np.array([.01, .04, .2, np.nan]))
        np.testing.assert_allclose(q, [.03, .06, .2, 1])
        np.testing.assert_allclose(fdr_q_values(np.array([.001, 1.])), [.002, 1.])

    def test_gaussian_center_stability_and_alignment(self) -> None:
        first = _gaussian_kernel(5.2, 8.1)
        second = _gaussian_kernel(5.5, 8.4)
        center_first = rf_maps(first.reshape(900, 1), 4)["centers"][0]
        center_second = rf_maps(second.reshape(900, 1), 4)["centers"][0]
        np.testing.assert_allclose(center_first, [5.2, 8.1], atol=.5)
        self.assertLess(np.linalg.norm(center_first - center_second), 1)
        aligned = align_kernels(first, center_first[None])
        peak = np.unravel_index(np.argmax(np.abs(aligned[0, :, :, 0])), (15, 15))
        self.assertEqual(peak, (7, 7))
        self.assertEqual(aligned.shape, first.shape)
        distant = _gaussian_kernel(10, 3)
        combined = np.concatenate((first, distant), axis=3)
        centers = np.vstack((center_first, rf_maps(distant.reshape(900, 1), 4)["centers"][0]))
        aligned_pair = align_kernels(combined, centers)
        before = pairwise_spatial_similarity(np.abs(combined[0]))["all"]
        after = pairwise_spatial_similarity(np.abs(aligned_pair[0]))["all"]
        self.assertGreater(after, before)

    def test_classification_and_representation_ignore_test_field(self) -> None:
        config = {"fdr_q_max": .05, "min_split_half_rf_r": .1,
                  "min_train_projection_r": .1}
        row = {"valid_trace": True, "shift_null_q_all_candidates_all_rois": .02,
               "split_half_rf_r": .4, "train_projection_r": .3,
               "center_stable": True, "test_r2": -100}
        self.assertEqual(classify_rf(row, config), "RF_RELIABLE")
        row["test_r2"] = 100
        self.assertEqual(classify_rf(row, config), "RF_RELIABLE")
        rows = [{"representation": kind, "fly_id": "fly1", "valid_trace": True,
                 "split_half_rf_r": .2, "train_projection_r": .3,
                 "split_half_center_distance": 1.0, "shift_null_p": .1,
                 "center_stable": True, "test_r2": -100}
                for kind in ("raw", "li_style_rf_relative", "causal_ema_residual_60s",
                             "causal_block_median_residual_60s")]
        expected = _representation_scores(rows)
        for entry in rows:
            entry["test_r2"] = 100
        self.assertEqual(_representation_scores(rows), expected)


if __name__ == "__main__":
    unittest.main()
