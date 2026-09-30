"""Frozen-grid Gaussian comparisons on Phase 6.3 spatial RFs."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.optimize import lsq_linear


def projection_matrix(size=15, steps=1000):
    """Average valid-pixel column projections of 1000 bilinearly rotated maps."""
    if size != 15 or steps < 1:
        raise ValueError('Expected frozen 15x15 RF and positive rotation count')
    yy, xx = np.mgrid[:size, :size].astype(float)
    xx -= 7
    yy -= 7
    matrix = np.zeros((size, size * size))
    for theta in 2 * np.pi * np.arange(steps) / steps:
        sx = np.cos(theta) * xx - np.sin(theta) * yy + 7
        sy = np.sin(theta) * xx + np.cos(theta) * yy + 7
        valid = (sx >= -1e-12) & (sx <= 14 + 1e-12) & (sy >= -1e-12) & (sy <= 14 + 1e-12)
        sx, sy = np.clip(sx, 0, 14), np.clip(sy, 0, 14)
        x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
        dx, dy = sx - x0, sy - y0
        counts = valid.sum(axis=0)
        for row, col in zip(*np.nonzero(valid), strict=True):
            scale = 1 / (steps * counts[col])
            for py, wy in ((y0[row, col], 1 - dy[row, col]), (min(y0[row, col] + 1, 14), dy[row, col])):
                for px, wx in ((x0[row, col], 1 - dx[row, col]), (min(x0[row, col] + 1, 14), dx[row, col])):
                    matrix[col, py * size + px] += scale * wy * wx
    return matrix


def rotational_profile(image, projector):
    if image.shape != (15, 15) or not np.isfinite(image).all():
        raise ValueError('Expected finite 15x15 Phase 6.3 mean RF')
    return projector @ image.ravel()


def lofo_training(profiles, heldout_index):
    """One profile per fly; held-out fly has exactly zero training weight."""
    profiles = np.asarray(profiles, dtype=float)
    if profiles.shape[0] != 5 or not 0 <= heldout_index < 5:
        raise ValueError('Expected exactly five fly profiles and a valid held-out index')
    return np.mean(np.delete(profiles, heldout_index, axis=0), axis=0)


@dataclass
class Fit:
    model: str
    baseline: float
    a1: float
    sigma1: float | None
    a2: float | None
    sigma2: float | None
    sse: float
    r2: float
    aic: float
    aicc: float
    bic: float
    at_bound: bool
    status: str
    prediction: np.ndarray
    near_sigma2_min: float | None = None
    near_sigma2_max: float | None = None
    near_a2_min: float | None = None
    near_a2_max: float | None = None


class GaussianGrid:
    """Search frozen widths; solve bounded linear coefficients at each width pair."""
    def __init__(self, x, config):
        self.x = np.asarray(x, dtype=float)
        self.config = config
        self.center = _grid(config['center_sigma_grid_px'])
        self.surround = _grid(config['surround_sigma_grid_px'])
        self.first = np.exp(-self.x[None, :] ** 2 / (2 * self.center[:, None] ** 2))
        self.second = np.exp(-self.x[None, :] ** 2 / (2 * self.surround[:, None] ** 2))
        self.pairs = [(i, j) for i, a in enumerate(self.center) for j, b in enumerate(self.surround)
                      if b - a >= config['minimum_sigma_separation_px'] - 1e-12]
        ones = np.ones_like(self.x)
        self.design1 = np.stack([np.column_stack((ones, g)) for g in self.first])
        self.design2 = np.stack([np.column_stack((ones, self.first[i], self.second[j]))
                                 for i, j in self.pairs])
        self.pinv1 = np.linalg.pinv(self.design1)
        self.pinv2 = np.linalg.pinv(self.design2)

    def fit(self, values, model):
        y = np.asarray(values, dtype=float)
        if y.shape != self.x.shape or not np.isfinite(y).all():
            raise ValueError('Expected finite 1D RF')
        if model == 'M0':
            b = float(np.clip(y.mean(), *self.config['baseline_bounds']))
            return self._result(model, y, np.full_like(y, b), b, 0, None, None, None)
        if model == 'M1':
            limits = [self.config['baseline_bounds'], self.config['center_amplitude_bounds']]
            coef, sse = _bounded_candidates(self.design1, self.pinv1 @ y, y, limits)
            index = int(np.argmin(sse))
            b, a = coef[index]
            return self._result(model, y, self.design1[index] @ coef[index], b, a, self.center[index], None, None)
        if model not in ('M2', 'M3'):
            raise ValueError(model)
        limits = [self.config['baseline_bounds'],
                  self.config['dog_center_amplitude_bounds'] if model == 'M3' else self.config['center_amplitude_bounds'],
                  self.config['dog_surround_amplitude_bounds'] if model == 'M3' else self.config['unconstrained_second_amplitude_bounds']]
        coef, sse = _bounded_candidates(self.design2, self.pinv2 @ y, y, limits)
        index = int(np.argmin(sse))
        b, a1, a2 = coef[index]
        i, j = self.pairs[index]
        fit = self._result(model, y, self.design2[index] @ coef[index], b, a1,
                           self.center[i], a2, self.surround[j])
        near = np.flatnonzero(sse <= sse[index] * np.exp(self.config['near_optimal_delta_aicc'] / len(y)))
        fit.near_sigma2_min = float(min(self.surround[self.pairs[k][1]] for k in near))
        fit.near_sigma2_max = float(max(self.surround[self.pairs[k][1]] for k in near))
        fit.near_a2_min = float(np.min(coef[near, 2]))
        fit.near_a2_max = float(np.max(coef[near, 2]))
        return fit

    def _result(self, model, y, predicted, b, a1, sigma1, a2, sigma2):
        n = len(y)
        k = {'M0': 1, 'M1': 3, 'M2': 5, 'M3': 5}[model]
        sse = float(np.sum((y - predicted) ** 2))
        total = float(np.sum((y - y.mean()) ** 2))
        aic = n * np.log(max(sse / n, np.finfo(float).tiny)) + 2 * k
        aicc = aic + 2 * k * (k + 1) / (n - k - 1) if n > k + 1 else np.nan
        bic = n * np.log(max(sse / n, np.finfo(float).tiny)) + k * np.log(n)
        limits = [(b, self.config['baseline_bounds'])]
        if model == 'M1':
            limits += [(a1, self.config['center_amplitude_bounds']),
                       (sigma1, self.config['center_sigma_grid_px'][:2])]
        if model in ('M2', 'M3'):
            limits += [(a1, self.config['dog_center_amplitude_bounds'] if model == 'M3' else self.config['center_amplitude_bounds']),
                       (a2, self.config['dog_surround_amplitude_bounds'] if model == 'M3' else self.config['unconstrained_second_amplitude_bounds']),
                       (sigma1, self.config['center_sigma_grid_px'][:2]),
                       (sigma2, self.config['surround_sigma_grid_px'][:2])]
        tol = self.config['bound_tolerance']
        hit = any(abs(value - bound) <= tol for value, bounds in limits for bound in bounds)
        status = 'AT_BOUND' if hit else 'OK'
        if model == 'M3' and (a2 <= tol or sigma2 >= self.surround[-1] - tol):
            status = 'SURROUND_POORLY_IDENTIFIED'
        return Fit(model, float(b), float(a1), None if sigma1 is None else float(sigma1),
                   None if a2 is None else float(a2), None if sigma2 is None else float(sigma2),
                   sse, 1 - sse / total if total > 0 else np.nan, float(aic), float(aicc),
                   float(bic), bool(hit), status, predicted)


def _bounded_candidates(design, coef, y, limits):
    """Exact constrained least-squares search, pruning by unconstrained SSE."""
    lo = np.array([a for a, _ in limits])
    hi = np.array([b for _, b in limits])
    raw_error = np.einsum('pni,pi->pn', design, coef) - y
    lower_sse = np.einsum('pn,pn->p', raw_error, raw_error)
    feasible = np.all((coef >= lo - 1e-12) & (coef <= hi + 1e-12), axis=1)
    answer = coef.copy()
    sse = np.where(feasible, lower_sse, np.inf)
    for index in np.argsort(lower_sse):
        if lower_sse[index] >= np.min(sse) - 1e-18:
            break
        if feasible[index]:
            continue
        result = lsq_linear(design[index], y, bounds=(lo, hi), tol=1e-12, max_iter=100)
        answer[index] = result.x
        sse[index] = float(np.sum((design[index] @ result.x - y) ** 2))
    if not np.isfinite(sse).any():
        raise RuntimeError('No bounded fit succeeded')
    return answer, sse


def _grid(spec):
    low, high, step = spec
    return np.arange(low, high + step / 2, step)
