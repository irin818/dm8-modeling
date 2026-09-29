"""Validate explicit feature, fold, preprocessing and model settings.

Inputs are a tracked JSON config and the frozen 9,000-update stimulus count.
No experiment hyperparameter is silently inferred from a test result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..datasets.splits import GlobalStimulusSplit
from ..features import FeatureDefinition


@dataclass(frozen=True)
class Phase5Config:
    raw: dict
    feature: FeatureDefinition
    folds: tuple[GlobalStimulusSplit, ...]

    @classmethod
    def load(cls, path: Path, stimulus_update_count: int = 9000) -> "Phase5Config":
        raw = json.loads(path.read_text())
        if raw.get("schema_version") != "phase5_config_v1":
            raise ValueError("Unsupported Phase 5 config schema")
        feature = FeatureDefinition(int(raw["feature"]["bins"]), int(raw["feature"]["updates_per_bin"]))
        if int(raw["feature"]["lag_count"]) != feature.history_updates:
            raise ValueError("lag_count must match bins * updates_per_bin")
        folds = tuple(GlobalStimulusSplit(row["name"], feature.history_updates,
                   int(row["train_end_update"]), int(row["validation_end_update"]),
                   int(row["test_end_update"])) for row in raw["folds"])
        if len(folds) < 2 or len({fold.name for fold in folds}) != len(folds):
            raise ValueError("At least two named temporal folds required")
        for fold in folds:
            fold.validate(stimulus_update_count)
        for name in ("ridge_alphas", "shared_alphas", "fly_penalties", "basis_head_alphas"):
            if not raw["model"][name] or min(raw["model"][name]) <= 0:
                raise ValueError(f"Positive {name} required")
        if not raw["model"]["basis_counts"] or min(raw["model"]["basis_counts"]) < 1:
            raise ValueError("Positive basis counts required")
        return cls(raw, feature, folds)
