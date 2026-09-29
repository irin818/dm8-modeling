"""Multi-output Ridge solves used by individual and shared linear models.

Input X [imaging frame, temporal-bin*pixel] and y [imaging frame,ROI].
Means and Gram matrices are computed only from the fit interval. Coefficients
have [feature,ROI] shape; alpha regularizes slopes but not intercepts.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RidgeFit:
    coefficient: np.ndarray
    intercept: np.ndarray
    alpha: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        return x.astype(np.float64) @ self.coefficient + self.intercept


@dataclass(frozen=True)
class RidgeSystem:
    mean_x: np.ndarray
    mean_y: np.ndarray
    eig_values: np.ndarray
    eig_vectors: np.ndarray
    transformed_cross: np.ndarray

    @classmethod
    def from_arrays(cls, x: np.ndarray, y: np.ndarray) -> "RidgeSystem":
        if x.ndim != 2 or y.ndim != 2 or len(x) != len(y) or len(x) < 2:
            raise ValueError("Expected matching [frame,feature] and [frame,ROI] arrays")
        xf, yf = x.astype(np.float64), y.astype(np.float64)
        mx, my = xf.mean(axis=0), yf.mean(axis=0)
        xc, yc = xf - mx, yf - my
        gram = xc.T @ xc / len(x)
        cross = xc.T @ yc / len(x)
        values, vectors = np.linalg.eigh(gram)
        return cls(mx, my, values, vectors, vectors.T @ cross)

    def fit(self, alpha: float) -> RidgeFit:
        if alpha <= 0:
            raise ValueError("Ridge alpha must be positive")
        coefficient = self.eig_vectors @ (self.transformed_cross / (self.eig_values[:, None] + alpha))
        return RidgeFit(coefficient, self.mean_y - self.mean_x @ coefficient, alpha)
