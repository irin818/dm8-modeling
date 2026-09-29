"""DEPRECATED COMPATIBILITY WRAPPER: single-pixel temporal model."""
from .models.linear.pixel_temporal import PixelResult, predict_pixel_model, fit_pixel_model, _fit
from .rf.null_tests import _shift_p_values, _bh_q_values, adjust_pixel_reports
