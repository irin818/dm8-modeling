"""DEPRECATED COMPATIBILITY WRAPPER: historical STA and feature functions."""
from .rf.sta import BaselineResult, fit_sta_baseline, _calibrated_prediction
from .features.lagged import lagged_design
from .preprocessing.fluorescence import causal_ema_residual
from .evaluation.legacy_metrics import _scores, _finite_or_none
