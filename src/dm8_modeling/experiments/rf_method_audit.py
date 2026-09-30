"""Phase 6.1b: descriptive TRAIN-only RF method and power audit."""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import numpy as np

from ..datasets import load_individual_datasets
from ..features.lagged import lagged_design
from ..io.stage_manifest import verify_stage_manifest
from ..io.tables import save_csv, save_json
from ..rf.characterization import characterize_halves, fdr_q_values
from .phase6 import _load_config
from .workflow import WorkflowContext


FINE_LAGS = 40  # Same 15-Hz, 2.67-s history as the frozen 4 x 10 baseline.
FRACTIONS = (0.25, 0.50, 0.75, 1.00)
KINDS = ("li_style_rf_relative", "raw", "causal_ema_residual_60s")
STRONG_LOCALIZER = re.compile(
    r"shifting[ _-]?bar|moving[ _-]?bar|locali[sz]er|rf[ _-]?center|"
    r"receptive[ _-]?field[ _-]?locali[sz]ation", re.I)


def learning_rows(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    """Nested, time-distributed TRAIN A samples; fixed full TRAIN B reference."""
    if (first.ndim != 1 or second.ndim != 1 or len(first) < 4 or len(second) < 4
            or np.intersect1d(first, second).size):
        raise ValueError("Expected two nonempty TRAIN halves")
    return np.arange(len(first)) % 4


def audit_localizers(root: Path) -> dict:
    """Read filenames and small text files only; never import or run source packages."""
    found = []
    searched = {}
    broad = re.compile(r"bar|mapping|position|azimuth|elevation|receptive[ _-]?field", re.I)
    broad_counts = {}
    for name in ("Dm8_module", "simulate", "outputs", "datasets",
                 "modeling_pipeline", "src", "docs", "configs"):
        base = root / name
        files = (sorted(path for path in base.rglob("*") if path.is_file() and
                        (root / "outputs/phase_06/rf_method_audit") not in path.parents)
                 if base.exists() else [])
        searched[name] = len(files)
        broad_counts[name] = 0
        for path in files:
            relative = path.relative_to(root).as_posix()
            name_match = STRONG_LOCALIZER.search(relative)
            content_match = False
            broad_match = bool(broad.search(relative))
            if path.suffix.lower() in {".json", ".md", ".py", ".txt", ".log", ".yaml", ".yml", ".csv", ".tsv"}:
                with path.open("rb") as handle:
                    contents = handle.read(2_000_000).decode("utf-8", errors="replace")
                content_match = bool(STRONG_LOCALIZER.search(contents))
                broad_match |= bool(broad.search(contents))
            broad_counts[name] += broad_match
            if name_match or content_match:
                found.append({"path": relative, "source_area": name,
                              "match": "filename" if name_match else "text",
                              "is_recorded_localizer": name == "Dm8_module"})
    # A name hit is a candidate, not proof: all candidates require inspection.
    return {"files_scanned": searched, "broad_keyword_file_counts": broad_counts,
            "candidates": found,
            "recorded_candidate_count": sum(row["is_recorded_localizer"] for row in found)}


def _old_rows(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _summary(rows: list[dict], representation: str, method: str) -> dict:
    selected = [row for row in rows if row["representation"] == representation and
                row["method"] == method and row["valid_trace"]]
    def median(key: str) -> float | None:
        values = [row[key] for row in selected if row[key] is not None and np.isfinite(row[key])]
        return float(np.median(values)) if values else None
    return {"method": method, "representation": representation, "valid_roi": len(selected),
            "median_split_half_rf_r": median("split_half_rf_r"),
            "median_projection_r": median("train_projection_r"),
            "median_center_displacement_px": median("center_displacement_px"),
            "center_within_2px": sum(row["center_displacement_px"] is not None and
                                     row["center_displacement_px"] <= 2 for row in selected)}


def _metrics(result: dict, item, kind: str, method: str, valid_base: np.ndarray,
             fraction: float = 1.0) -> list[dict]:
    rows = []
    for i, roi in enumerate(item.roi_labels):
        distance = float(result["center_displacement"][i])
        valid = bool(valid_base[i] and not result["invalid_trace"][i] and
                     np.isfinite(result["center"][i]).all())
        rows.append({"fly_id": item.fly_id, "roi_id": roi, "representation": kind,
                     "method": method, "train_a_fraction": fraction, "valid_trace": valid,
                     "split_half_rf_r": float(result["split_half_rf_r"][i]),
                     "train_projection_r": float(result["train_projection_r"][i]),
                     "center_displacement_px": distance if np.isfinite(distance) else None,
                     "center_row": float(result["center"][i, 0]) if np.isfinite(result["center"][i, 0]) else None,
                     "center_col": float(result["center"][i, 1]) if np.isfinite(result["center"][i, 1]) else None,
                     "shift_null_p": float(result["shift_null_p"][i]) if valid else 1.0})
    return rows


def run_rf_method_audit(root: Path) -> Path:
    root = root.expanduser().resolve()
    context = WorkflowContext.load(root)
    config, phase5 = _load_config(root)
    fold = next(fold for fold in phase5.folds if fold.name == config["train_fold"])
    verify_stage_manifest(context.stage_dir(7) / "stage_manifest.json", context.config)
    for name in ("response", "reliability", "alignment"):
        verify_stage_manifest(context.output_root / "phase_06" / name /
                              "stage_manifest.json", config)
    out = context.output_root / "phase_06" / "rf_method_audit"
    out.mkdir(parents=True, exist_ok=True)
    old_path = context.output_root / "phase_06" / "reliability" / "all_representation_rf_metrics.csv"
    old_hash = hashlib.sha256(old_path.read_bytes()).hexdigest()
    old = _old_rows(old_path)
    items = load_individual_datasets(context.data_root, phase5.feature, fold)
    rows, curves, frame_counts = [], [], {}
    for item in items:
        saved = np.load(context.output_root / "phase_06" / "response" /
                        f"{item.fly_id}_train_responses.npz")
        first, second = saved["first_dataset_rows"], saved["second_dataset_rows"]
        assert np.all(item.split_label[first] == 0) and np.all(item.split_label[second] == 0)
        assert FINE_LAGS == item.feature_definition.history_updates
        first_fine = lagged_design(item.aligned.stimulus, item.update_index[first], FINE_LAGS)
        second_fine = lagged_design(item.aligned.stimulus, item.update_index[second], FINE_LAGS)
        first_coarse, second_coarse = item.features(first), item.features(second)
        modulo = learning_rows(first, second)
        frame_counts[item.fly_id] = {fraction: int(np.sum(modulo < int(round(fraction * 4))))
                                     for fraction in FRACTIONS}
        interval_s = float(np.median(np.diff(item.imaging_time_us)) / 1_000_000)
        exclusion = int(np.ceil(config["null_exclusion_seconds"] / interval_s))
        raw = item.y_raw[np.r_[first, second]]
        valid_base = np.mean(raw == 0, axis=0) < config["max_train_zero_fraction"]
        for kind in KINDS:
            first_y = saved[f"{kind}_first"].astype(np.float32)
            second_y = saved[f"{kind}_second"].astype(np.float32)
            # Coarse must reproduce the saved historical Li-style result.
            if kind == "li_style_rf_relative":
                coarse = characterize_halves(first_coarse, first_y, second_coarse,
                                             second_y, 4, exclusion)
                rows.extend(_metrics(coarse, item, kind, "coarse_4x10", valid_base))
            fine = characterize_halves(first_fine, first_y, second_fine,
                                       second_y, FINE_LAGS, exclusion)
            rows.extend(_metrics(fine, item, kind, "fine_40x1", valid_base))
            if kind == "li_style_rf_relative":
                for fraction in FRACTIONS:
                    chosen = modulo < int(round(fraction * 4))
                    result = fine if fraction == 1 else characterize_halves(
                        first_fine[chosen], first_y[chosen], second_fine, second_y,
                        FINE_LAGS, exclusion)
                    curves.extend(_metrics(result, item, kind, "fine_40x1", valid_base, fraction))
    # Explicit families: the old 944-test family stays untouched, and both
    # 236-test Li families are labeled exploratory.
    historical = [row for row in old if row["representation"] == "li_style_rf_relative"]
    historical_lookup = {(row["fly_id"], row["roi_id"]): row for row in historical}
    coarse_difference = {key: 0.0 for key in ("split_half_rf_r", "train_projection_r",
                                               "split_half_center_distance", "shift_null_p")}
    for row in rows:
        if row["method"] != "coarse_4x10":
            continue
        old_row = historical_lookup[row["fly_id"], row["roi_id"]]
        if not row["valid_trace"]:
            continue
        for old_key, new_key in (("split_half_rf_r", "split_half_rf_r"),
                                 ("train_projection_r", "train_projection_r"),
                                 ("split_half_center_distance", "center_displacement_px"),
                                 ("shift_null_p", "shift_null_p")):
            delta = abs(float(old_row[old_key]) - float(row[new_key]))
            coarse_difference[old_key] = max(coarse_difference[old_key], delta)
    if any(value > 1e-5 for value in coarse_difference.values()):
        raise AssertionError(f"Historical coarse RF was not reproduced: {coarse_difference}")
    old_q = fdr_q_values(np.array([float(row["shift_null_p"]) if row["valid_trace"] == "True" else 1
                                 for row in old]))
    old_li_q = [old_q[i] for i, row in enumerate(old) if row["representation"] == "li_style_rf_relative"]
    for method in ("coarse_4x10", "fine_40x1"):
        subset = [row for row in rows if row["method"] == method and
                  row["representation"] == "li_style_rf_relative"]
        q = fdr_q_values(np.array([row["shift_null_p"] for row in subset]))
        for row, value in zip(subset, q, strict=True):
            row["exploratory_li_236_q"] = float(value)
    save_csv(out / "temporal_comparison_roi.csv", rows)
    save_csv(out / "learning_curve_roi.csv", curves)
    localizer = audit_localizers(root)
    save_json(out / "localizer_search.json", localizer)
    old_li_p = np.array([float(row["shift_null_p"]) if row["valid_trace"] == "True" else 1
                         for row in historical])
    family = {"historical_944": {"hypotheses": len(old), "li_raw_p_below_0_05": int(sum(old_li_p < .05)),
                                 "li_bh_q_below_0_05": int(sum(np.asarray(old_li_q) < .05)),
                                 "minimum_li_q": float(min(old_li_q))},
              "exploratory_coarse_li_236": {"hypotheses": len(historical),
                    "raw_p_below_0_05": int(sum(old_li_p < .05)),
                    "bh_q_below_0_05": int(sum(fdr_q_values(old_li_p) < .05)),
                    "minimum_q": float(min(fdr_q_values(old_li_p)))}}
    fine_li = [row for row in rows if row["representation"] == "li_style_rf_relative" and
               row["method"] == "fine_40x1"]
    family["exploratory_fine_li_236"] = {
        "hypotheses": len(fine_li), "raw_p_below_0_05": sum(row["shift_null_p"] < .05 for row in fine_li),
        "bh_q_below_0_05": sum(row["exploratory_li_236_q"] < .05 for row in fine_li),
        "minimum_q": min(row["exploratory_li_236_q"] for row in fine_li)}
    summary = {"status": "EXPLORATORY REANALYSIS", "fine_lags": FINE_LAGS,
               "train_only": True, "historical_metrics_sha256": old_hash,
               "historical_coarse_max_absolute_difference": coarse_difference,
               "temporal": [_summary(rows, kind, method) for kind in KINDS
                            for method in (("coarse_4x10", "fine_40x1") if kind == "li_style_rf_relative" else ("fine_40x1",))],
               "by_fly": [{"fly_id": fly, **_summary([row for row in rows if row["fly_id"] == fly],
                                                  "li_style_rf_relative", method)}
                          for fly in sorted({item.fly_id for item in items})
                          for method in ("coarse_4x10", "fine_40x1")],
               "learning_curve": [{"train_a_fraction": fraction, "train_a_frames_per_fly":
                                   {item.fly_id: frame_counts[item.fly_id][fraction] for item in items},
                                   **_summary([row for row in curves if row["train_a_fraction"] == fraction],
                                              "li_style_rf_relative", "fine_40x1")}
                                  for fraction in FRACTIONS],
               "family": family, "localizer_recorded_candidates": localizer["recorded_candidate_count"]}
    return save_json(out / "summary.json", summary)
