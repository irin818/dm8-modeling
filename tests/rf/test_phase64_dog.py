"""Phase 6.4 model, projection, biological weighting, and input-integrity checks."""
import hashlib
import json
from pathlib import Path
import unittest
import numpy as np

from dm8_modeling.rf.dog import GaussianGrid, lofo_training, projection_matrix

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT/'configs/phase6_4_dog_test.json').read_text())
X = np.arange(-7, 8)
G = GaussianGrid(X, CONFIG)
NOISE = 1e-5*np.sin(1.3*X)


class Phase64Tests(unittest.TestCase):
    def test_single_gaussian_recovers_center(self):
        y=.001-.008*np.exp(-X*X/(2*1.5**2))+NOISE
        m=G.fit(y,'M1')
        self.assertAlmostEqual(m.a1,-.008,delta=.0001)
        self.assertAlmostEqual(m.sigma1,1.5,delta=.25)

    def test_true_dog_beats_single(self):
        y=.001-.008*np.exp(-X*X/(2*1.25**2))+.004*np.exp(-X*X/(2*4.5**2))+NOISE
        m1,m3=G.fit(y,'M1'),G.fit(y,'M3')
        self.assertGreater(m1.aicc-m3.aicc,2)
        self.assertLess(m3.a1,0)
        self.assertGreater(m3.a2,0)
        self.assertAlmostEqual(m3.sigma2,4.5,delta=.5)

    def test_same_sign_pair_is_not_classic_dog(self):
        y=.001-.007*np.exp(-X*X/(2*1.0**2))-.003*np.exp(-X*X/(2*4.5**2))+NOISE
        m1,m2,m3=(G.fit(y,k) for k in ('M1','M2','M3'))
        self.assertGreater(m1.aicc-m2.aicc,2)
        self.assertLess(m2.a2,0)
        self.assertGreater(m3.aicc,m2.aicc)

    def test_no_surround_not_declared_dog(self):
        y=-.006*np.exp(-X*X/(2*1.5**2))+NOISE
        m1,m3=G.fit(y,'M1'),G.fit(y,'M3')
        self.assertGreater(m3.aicc,m1.aicc)
        self.assertTrue(m3.a2<1e-4 or m3.status=='SURROUND_POORLY_IDENTIFIED')

    def test_bound_hit_is_visible(self):
        y=-.01*np.exp(-X*X/(2*.5**2))+NOISE
        self.assertTrue(G.fit(y,'M1').at_bound)

    def test_rotational_projection_of_symmetric_map(self):
        p=projection_matrix(15,1000)
        yy,xx=np.mgrid[-7:8,-7:8]
        image=np.exp(-(xx*xx+yy*yy)/(2*2**2))
        profile=p@image.ravel()
        np.testing.assert_allclose(profile,profile[::-1],atol=1e-12)
        self.assertEqual(int(np.argmax(profile)),7)
        np.testing.assert_allclose(p.sum(axis=1),np.ones(15),atol=1e-12)

    def test_lofo_excludes_heldout(self):
        data=np.arange(5*15,dtype=float).reshape(5,15)
        original=lofo_training(data,2)
        data[2]+=100000
        np.testing.assert_array_equal(lofo_training(data,2),original)

    def test_equal_fly_weight_ignores_roi_counts(self):
        profiles=np.array([np.full(15,1),np.full(15,2),np.full(15,3),np.full(15,4),np.full(15,100)])
        self.assertAlmostEqual(lofo_training(profiles,0)[0],27.25)

    def test_phase63_input_is_unchanged(self):
        path=ROOT/CONFIG['phase63_arrays']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),CONFIG['phase63_arrays_sha256'])


if __name__=='__main__': unittest.main()
