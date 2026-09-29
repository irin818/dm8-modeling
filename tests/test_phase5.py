"""Leakage, provenance and interpretable shared-filter regression checks."""

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from dm8_modeling.datasets.individual import IndividualDataset
from dm8_modeling.datasets.integrated import build_integrated_dataset
from dm8_modeling.datasets.splits import GlobalStimulusSplit, TRAIN, VALIDATION, TEST
from dm8_modeling.features import FeatureDefinition
from dm8_modeling.preprocessing.normalization import fit_response_scaler
from dm8_modeling.models.population.shared_strf import fit_shared_strf
from dm8_modeling.experiments.registry import write_registry


class Phase5Contracts(unittest.TestCase):
    def test_registry_preserves_other_models_when_one_is_rerun(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "registry.csv"
            write_registry([{"experiment_id": "model_a", "model": "a"},
                            {"experiment_id": "model_b", "model": "b"}], path)
            write_registry([{"experiment_id": "model_a", "model": "a_v2"}], path)
            lines = path.read_text().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertIn("model_b", lines[2])
            self.assertIn("a_v2", lines[1])

    def test_global_split_purges_every_causal_history(self):
        split = GlobalStimulusSplit("synthetic", 4, 25, 36, 50)
        updates = np.arange(3, 50)
        labels = split.labels(updates, 50)
        train = set(updates[labels == TRAIN])
        validation = set(updates[labels == VALIDATION])
        test = set(updates[labels == TEST])
        def histories(indices):
            return {u - lag for u in indices for lag in range(4)}
        self.assertFalse(histories(train) & histories(validation))
        self.assertFalse(histories(validation) & histories(test))
        self.assertEqual(split.labels(updates, 50).tolist(), labels.tolist())

    def test_train_scaler_ignores_validation_and_test_values(self):
        response = np.array([[1.], [3.], [100.], [200.]])
        train = np.array([True, True, False, False])
        first = fit_response_scaler(response, train, "train_zscore")
        response[2:] *= 1000
        second = fit_response_scaler(response, train, "train_zscore")
        np.testing.assert_array_equal(first.mean, second.mean)
        np.testing.assert_array_equal(first.scale, second.scale)
        self.assertEqual(first.mean[0], 2)

    def test_integrated_rows_trace_back_to_original_response(self):
        definition = FeatureDefinition(1, 1)
        table = np.zeros((5, 225), dtype=np.float32)
        table[:, 4] = np.arange(5)
        individuals = []
        for fly in ("fly1", "fly2"):
            aligned = SimpleNamespace(session=SimpleNamespace(fly=fly, run_id="run"),
                roi_labels=["R1", "R2"], qc={"source_sha256": {"Results.csv": fly}})
            individuals.append(IndividualDataset(aligned, table, definition,
                np.array([1, 3]), np.array([[11., 12.], [31., 32.]], dtype=np.float32),
                np.array([100, 300]), np.array([7, 9]), np.array([TRAIN, TEST], dtype=np.uint8)))
        long = build_integrated_dataset(individuals)
        self.assertEqual(long.X.shape, (8, 225))
        self.assertEqual(long.unique_stimulus_update_count, 2)
        self.assertEqual(long.explain_row(5)["fly_id"], "fly2")
        self.assertEqual(long.explain_row(5)["roi_id"], "R2")
        self.assertEqual(long.explain_row(5)["Results_csv_frame_one_based"], 8)
        self.assertEqual(long.explain_row(5)["response"], 12)
        self.assertEqual(long.X[5, 4], 1)
        with self.assertRaises(MemoryError):
            long.X.materialize(max_bytes=1)

    def test_shared_model_recovers_synthetic_common_filter(self):
        rng = np.random.default_rng(4)
        table = rng.normal(size=(360, 225)).astype(np.float32)
        table[:, 0] = rng.normal(size=360)
        label = np.full(360, TEST, dtype=np.uint8)
        label[:220] = TRAIN
        label[220:290] = VALIDATION
        individuals, processed = [], {}
        for fly, gain in (("fly1", 1.2), ("fly2", -0.8)):
            aligned = SimpleNamespace(session=SimpleNamespace(fly=fly, run_id="run"),
                roi_labels=["R1"], qc={"source_sha256": {}})
            target = (gain * table[:, 0] + 0.03 * rng.normal(size=360))[:, None].astype(np.float32)
            item = IndividualDataset(aligned, table, FeatureDefinition(1, 1), np.arange(360),
                                     target, np.arange(360), np.arange(360), label)
            individuals.append(item)
            processed[fly] = SimpleNamespace(values=target)
        fit = fit_shared_strf(individuals, processed, (0.01, 0.1), iterations=3)
        for item in individuals:
            actual = processed[item.fly_id].values[label == TEST, 0]
            predicted = fit.predictions[item.fly_id][label == TEST, 0]
            self.assertGreater(np.corrcoef(actual, predicted)[0, 1], 0.8)


if __name__ == "__main__":
    unittest.main()
