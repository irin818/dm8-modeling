"""Indexed long-format features cannot silently materialize a huge duplicate X."""
import unittest
import numpy as np
from dm8_modeling.datasets.integrated import IndexedFeatureMatrix


class IntegratedFeatureContract(unittest.TestCase):
    def test_indexed_view_and_memory_guard(self):
        table = np.arange(12, dtype=np.float32).reshape(4, 3)
        view = IndexedFeatureMatrix(table, np.array([2, 2, 0]))
        np.testing.assert_array_equal(view[0], [6., 7., 8.])
        self.assertEqual(view[1, 2], 8.)
        with self.assertRaises(MemoryError):
            view.materialize(max_bytes=1)
