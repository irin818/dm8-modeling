"""Latest already-presented stimulus and exclusive payload end."""
import unittest
import numpy as np
from dm8_modeling.data.clocks import associate_imaging_with_updates


class AlignmentClockContract(unittest.TestCase):
    def test_exact_onset_and_payload_end(self):
        update = np.array([100, 200, 300], dtype=np.int64)
        imaging = np.array([99, 100, 199, 200, 399, 400], dtype=np.int64)
        index, included = associate_imaging_with_updates(update, imaging, 400)
        np.testing.assert_array_equal(index, [-1, 0, 0, 1, 2, 2])
        np.testing.assert_array_equal(included, [False, True, True, True, True, False])
