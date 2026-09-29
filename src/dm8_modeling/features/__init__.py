"""Causal stimulus-history features shared by individual and multi-fly models."""

from .temporal_basis import FeatureDefinition, build_shared_feature_table

__all__ = ["FeatureDefinition", "build_shared_feature_table"]
