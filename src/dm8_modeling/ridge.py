"""DEPRECATED COMPATIBILITY WRAPPER: binned STRF and temporal design."""
from .models.linear.binned_strf import RidgeResult, fit_binned_ridge, _ridge_fit, _predict
from .features.temporal_basis import binned_design
