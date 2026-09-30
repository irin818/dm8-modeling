"""Phase 6.1: TRAIN-only response reconstruction and RF characterization.

This entry never fits a predictive model or reads VALIDATION/TEST responses
for representation choice, ROI inclusion, RF center, or alignment.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..datasets import load_individual_datasets
from ..datasets.splits import TRAIN
from ..io.stage_manifest import verify_stage_manifest, write_stage_manifest
from ..io.tables import save_csv, save_json
from ..preprocessing.fluorescence import candidate_response
from ..preprocessing.rf_response import li_style_relative_response
from ..rf.characterization import (align_kernels, characterize_halves, classify_rf, fdr_q_values,
                                   pairwise_spatial_similarity)
from .config import Phase5Config
from .workflow import WorkflowContext


KINDS = ("raw", "li_style_rf_relative", "causal_ema_residual_60s",
         "causal_block_median_residual_60s")


def _finite(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _load_config(root: Path) -> tuple[dict, Phase5Config]:
    raw = json.loads((root / "configs/phase6_rf.json").read_text())
    if raw.get("schema_version") != "phase6_rf_v1" or tuple(raw.get("response_kinds", ())) != KINDS:
        raise ValueError("Unsupported Phase 6 RF config or response family")
    if raw["train_half_gap_updates_each_side"] < 40 or raw["li_gaussian_sigma_seconds"] <= 0:
        raise ValueError("Insufficient temporal purge or invalid Gaussian width")
    phase5 = Phase5Config.load(root / raw["phase5_config"])
    if raw["train_fold"] not in {fold.name for fold in phase5.folds}:
        raise ValueError("Unknown Phase 6 training fold")
    return raw, phase5


def _train_halves(item, config: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Keep disjoint TRAIN stimulus histories and discard Gaussian edges."""
    train = np.flatnonzero(item.split_label == TRAIN)
    if len(train) < 1000:
        raise ValueError("Too few TRAIN frames for split-half RF")
    midpoint = int(np.median(item.update_index[train]))
    gap = int(config["train_half_gap_updates_each_side"])
    first = train[item.update_index[train] < midpoint - gap]
    second = train[item.update_index[train] >= midpoint + gap]
    if len(first) < 100 or len(second) < 100:
        raise ValueError("Insufficient independent TRAIN halves")
    eligible = np.flatnonzero(item.aligned.update_index >= item.feature_definition.history_updates - 1)
    raw = item.aligned.response
    time = item.aligned.imaging_time_us
    first_full, second_full = eligible[first], eligible[second]
    first_li, margin_a = li_style_relative_response(
        raw[first_full], time[first_full], config["li_gaussian_sigma_seconds"],
        config["li_edge_truncate_sigma"])
    second_li, margin_b = li_style_relative_response(
        raw[second_full], time[second_full], config["li_gaussian_sigma_seconds"],
        config["li_edge_truncate_sigma"])
    first, second = first[margin_a:-margin_a], second[margin_b:-margin_b]
    first_li, second_li = first_li[margin_a:-margin_a], second_li[margin_b:-margin_b]
    if len(first) < 200 or len(second) < 200:
        raise ValueError("Too few TRAIN rows after Li-style Gaussian edge exclusion")
    if np.max(item.update_index[first]) >= np.min(item.update_index[second]) - item.feature_definition.history_updates:
        raise ValueError("TRAIN halves have overlapping stimulus histories")
    return first, second, first_li, second_li


def _responses(item, first: np.ndarray, second: np.ndarray,
               first_li: np.ndarray, second_li: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    eligible = np.flatnonzero(item.aligned.update_index >= item.feature_definition.history_updates - 1)
    raw = item.aligned.response
    time = item.aligned.imaging_time_us
    values = {"li_style_rf_relative": (first_li, second_li)}
    for kind in KINDS:
        if kind == "li_style_rf_relative":
            continue
        # The full trace is used only by past-only transformations. Selecting
        # TRAIN rows afterwards cannot introduce future response information.
        processed = candidate_response(raw, time, kind)
        values[kind] = (processed[eligible[first]], processed[eligible[second]])
    return values


def _provenance(item, config: dict, first: np.ndarray, second: np.ndarray) -> dict:
    raw_path = item.aligned.session.path / "Results.csv"
    source_hash = item.aligned.qc["source_sha256"]["Results.csv"]
    transformations = []
    for kind in KINDS:
        offline = kind == "li_style_rf_relative"
        parameters = ({"sigma_seconds": config["li_gaussian_sigma_seconds"],
                       "truncate_sigma": config["li_edge_truncate_sigma"],
                       "segment_policy": ("separate TRAIN halves, reflected edges, discard "
                                          f"{config['li_edge_truncate_sigma']}-sigma margins"),
                       "time_step": "median Zeiss frame-out interval"} if offline else
                      {"tau_seconds": 60.0} if kind == "causal_ema_residual_60s" else
                      {"past_window_seconds": 60.0, "refresh_seconds": 10.0} if
                      kind == "causal_block_median_residual_60s" else {})
        transformations.append({"name": kind,
                                "transformation": (f"F - Gaussian_{config['li_gaussian_sigma_seconds']}s(F)"
                                                   if offline else kind),
                                "parameters": parameters, "causal": not offline,
                                "scientific_purpose": "NON-CAUSAL / OFFLINE RF CHARACTERIZATION ONLY" if offline
                                else "TRAIN RF comparison; potential future predictive target",
                                "upstream_source": str(raw_path), "source_raw_sha256": source_hash})
    return {"fly_id": item.fly_id, "run_id": item.run_id,
            "source_raw_path": str(raw_path), "source_raw_sha256": source_hash,
            "raw_anchor_kind": "raw/near-raw ROI mean GCaMP fluorescence intensity, not official dF/F",
            "roi_interpretation_evidence": "WORKING_BIOLOGICAL_ASSUMPTION",
            "train_fold": config["train_fold"], "first_train_rows": len(first),
            "second_train_rows": len(second), "first_original_results_rows":
            [int(item.original_sample_index[first[0]]), int(item.original_sample_index[first[-1]])],
            "second_original_results_rows":
            [int(item.original_sample_index[second[0]]), int(item.original_sample_index[second[-1]])],
            "transformations": transformations}


def _representation_scores(rows: list[dict]) -> dict[str, dict]:
    """Fly-balanced TRAIN-only score; no per-ROI TEST-informed choice."""
    result = {}
    for kind in KINDS:
        per_fly = []
        for fly in sorted({row["fly_id"] for row in rows}):
            subset = [row for row in rows if row["representation"] == kind and row["fly_id"] == fly
                      and row["valid_trace"]]
            if not subset:
                continue
            median_split = float(np.median([row["split_half_rf_r"] for row in subset]))
            median_projection = float(np.median([row["train_projection_r"] for row in subset]))
            per_fly.append((median_split + median_projection) / 2)
        valid = [row for row in rows if row["representation"] == kind and row["valid_trace"]]
        distances = [row["split_half_center_distance"] for row in valid if
                     row["split_half_center_distance"] is not None]
        result[kind] = {"fly_balanced_train_rf_score": float(np.mean(per_fly)) if per_fly else None,
                        "fly_count": len(per_fly), "valid_roi": len(valid),
                        "median_split_half_rf_r": float(np.median([row["split_half_rf_r"] for row in valid]))
                        if valid else None,
                        "median_train_projection_r": float(np.median([row["train_projection_r"] for row in valid]))
                        if valid else None,
                        "median_center_displacement_pixels": float(np.median(distances)) if distances else None,
                        "uncorrected_shift_p_below_0_05": sum(row["shift_null_p"] < .05 for row in valid),
                        "center_stable_roi": sum(row["center_stable"] for row in valid)}
    return result


def _choose_representation(scores: dict[str, dict], candidates: tuple[str, ...],
                           clear_gain: float) -> str:
    best = max(candidates, key=lambda kind: scores[kind]["fly_balanced_train_rf_score"]
               if scores[kind]["fly_balanced_train_rf_score"] is not None else -np.inf)
    raw = scores["raw"]["fly_balanced_train_rf_score"]
    gain = scores[best]["fly_balanced_train_rf_score"] - raw
    return best if best != "raw" and gain >= clear_gain else "raw"


def run_phase6(root: Path) -> Path:
    """Run response (A), reliability (B), center/alignment readiness (C)."""
    root = root.expanduser().resolve()
    context = WorkflowContext.load(root)
    config, phase5 = _load_config(root)
    fold = next(fold for fold in phase5.folds if fold.name == config["train_fold"])
    previous = context.stage_dir(7) / "stage_manifest.json"
    verify_stage_manifest(previous, context.config)
    items = load_individual_datasets(context.data_root, phase5.feature, fold)
    roi_count = sum(len(item.roi_labels) for item in items)

    out = context.output_root / "phase_06"
    response_dir, rf_dir, align_dir = (out / name for name in ("response", "reliability", "alignment"))
    for directory in (response_dir, rf_dir, align_dir):
        directory.mkdir(parents=True, exist_ok=True)
    response_outputs, rf_outputs = [], []
    summaries, metrics = [], []
    computed = {}
    for item in items:
        first, second, first_li, second_li = _train_halves(item, config)
        representations = _responses(item, first, second, first_li, second_li)
        trace_hash = item.aligned.qc["source_sha256"]["Results.csv"]
        for kind, (first_y, second_y) in representations.items():
            processed = np.vstack((first_y, second_y))
            for roi, label in enumerate(item.roi_labels):
                raw = item.y_raw[np.r_[first, second], roi]
                summaries.append({"fly_id": item.fly_id, "roi_id": label, "representation": kind,
                                  "source_raw_sha256": trace_hash,
                                  "raw_train_mean": float(np.mean(raw)),
                                  "raw_train_std": float(np.std(raw)),
                                  "processed_train_mean": float(np.mean(processed[:, roi])),
                                  "processed_train_std": float(np.std(processed[:, roi])),
                                  "train_zero_fraction": float(np.mean(raw == 0)),
                                  "train_invalid_fraction": float(np.mean(~np.isfinite(raw)))})
        response_path = response_dir / f"{item.fly_id}_train_responses.npz"
        np.savez_compressed(response_path, first_dataset_rows=first, second_dataset_rows=second,
                            first_original_results_rows=item.original_sample_index[first],
                            second_original_results_rows=item.original_sample_index[second],
                            **{f"{kind}_first": pair[0] for kind, pair in representations.items()},
                            **{f"{kind}_second": pair[1] for kind, pair in representations.items()})
        provenance = save_json(response_dir / f"{item.fly_id}_provenance.json",
                               _provenance(item, config, first, second))
        response_outputs.extend((response_path, provenance))

        first_x, second_x = item.features(first).astype(float), item.features(second).astype(float)
        interval_s = float(np.median(np.diff(item.imaging_time_us)) / 1_000_000)
        exclusion = int(np.ceil(config["null_exclusion_seconds"] / interval_s))
        for kind in KINDS:
            first_y, second_y = representations[kind]
            result = characterize_halves(first_x, first_y.astype(float), second_x,
                                         second_y.astype(float), phase5.feature.bins, exclusion)
            computed[item.fly_id, kind] = result
            kernel_path = rf_dir / f"{item.fly_id}_{kind}_rf.npz"
            np.savez_compressed(kernel_path, roi_labels=np.asarray(item.roi_labels),
                                kernel_first=result["kernel_first"].astype(np.float32),
                                kernel_second=result["kernel_second"].astype(np.float32),
                                kernel_full=result["kernel_full"].astype(np.float32),
                                kernel_full_zscore=result["kernel_full_zscore"].astype(np.float32),
                                spatial=result["spatial"].astype(np.float32),
                                temporal=result["temporal"].astype(np.float32),
                                center=result["center"], center_first=result["center_first"],
                                center_second=result["center_second"])
            rf_outputs.append(kernel_path)
            for roi, label in enumerate(item.roi_labels):
                zero_fraction = float(np.mean(item.y_raw[np.r_[first, second], roi] == 0))
                reason = ("constant_train_half" if result["invalid_trace"][roi] else
                          "excess_train_zeros" if zero_fraction >= config["max_train_zero_fraction"] else
                          "center_fit_unresolved" if not np.isfinite(result["center"][roi]).all() else "")
                valid = (not result["invalid_trace"][roi] and zero_fraction <
                         config["max_train_zero_fraction"] and
                         np.isfinite(result["center"][roi]).all())
                metrics.append({"fly_id": item.fly_id, "roi_id": label,
                                "representation": kind, "valid_trace": bool(valid),
                                "invalid_trace_reason": reason,
                                "split_half_rf_r": float(result["split_half_rf_r"][roi]),
                                "train_projection_r": float(result["train_projection_r"][roi]),
                                "shift_null_p": float(result["shift_null_p"][roi]),
                                "train_zero_fraction": zero_fraction,
                                "center_row": _finite(result["center"][roi, 0]),
                                "center_col": _finite(result["center"][roi, 1]),
                                "center_first_row": _finite(result["center_first"][roi, 0]),
                                "center_first_col": _finite(result["center_first"][roi, 1]),
                                "center_second_row": _finite(result["center_second"][roi, 0]),
                                "center_second_col": _finite(result["center_second"][roi, 1]),
                                "center_fit_uncertainty_heuristic": _finite(
                                    result["center_fit_uncertainty_heuristic"][roi]),
                                "center_uncertainty": _finite(
                                    result["center_fit_uncertainty_heuristic"][roi]),
                                "center_uncertainty_kind": "1-minus-min-axis-Gaussian-fit-R2 heuristic; not CI",
                                "split_half_center_distance": _finite(result["center_displacement"][roi]),
                                "center_stable": bool(result["center_displacement"][roi] <=
                                                      config["max_center_displacement_pixels"]),
                                "dominant_temporal_bin": int(result["dominant_bin"][roi]),
                                "effect_size": float(result["train_projection_r"][roi]),
                                "source_raw_sha256": trace_hash})

    response_summary = save_csv(response_dir / "response_summary.csv", summaries)
    response_outputs.append(response_summary)
    response_manifest = write_stage_manifest("phase_06_1A_response_reconstruction", response_dir,
        config, [previous, root / "configs/phase6_rf.json", root / config["phase5_config"],
                 *(item.aligned.session.path / "Results.csv" for item in items)],
        response_outputs, root, details={"train_fold": fold.name, "roi_count": roi_count,
                                         "noncausal_representation": "li_style_rf_relative"})

    q = fdr_q_values(np.array([row["shift_null_p"] if row["valid_trace"] else 1.0
                             for row in metrics]))
    for row, value in zip(metrics, q, strict=True):
        row["shift_null_q_all_candidates_all_rois"] = float(value)
    scores = _representation_scores(metrics)
    for kind in KINDS:
        scores[kind]["fdr_q_below_0_05"] = sum(
            row["representation"] == kind and row["valid_trace"] and
            row["shift_null_q_all_candidates_all_rois"] < .05 for row in metrics)
    rf_kind = _choose_representation(scores, KINDS, config["representation_clear_gain"])
    predictive_kind = _choose_representation(
        scores, ("raw", "causal_ema_residual_60s", "causal_block_median_residual_60s"),
        config["representation_clear_gain"])
    score_path = save_json(rf_dir / "representation_comparison.json",
        {"scores": scores, "selected_rf_representation": rf_kind,
         "selected_future_predictive_representation": predictive_kind,
         "selection_rule": "TRAIN-only fly-balanced mean of median split-half RF r and median A-to-B projection r; require >= clear_gain over raw",
         "fdr_family": f"all {len(KINDS)} response representations x all {roi_count} ROI columns",
         "no_validation_or_test_response_used": True})
    metrics_path = save_csv(rf_dir / "all_representation_rf_metrics.csv", metrics)
    rf_outputs.extend((score_path, metrics_path))
    rf_manifest = write_stage_manifest("phase_06_1B_rf_reliability", rf_dir, config,
        [response_manifest, *response_outputs], rf_outputs, root,
        details={"candidate_tests": len(metrics), "selected_rf_representation": rf_kind})

    selected = []
    selected_kernels, selected_centers, selected_groups = [], [], []
    fly_summaries, fly_mean_paths = [], []
    for item in items:
        fly_rows = [row.copy() for row in metrics if row["fly_id"] == item.fly_id and
                    row["representation"] == rf_kind]
        for row in fly_rows:
            row["rf_classification"] = classify_rf(row, config)
            row["selected_rf_representation"] = rf_kind
            row["selected_future_predictive_representation"] = predictive_kind
            row["center_method"] = "dominant-bin polarity-oriented row/column Gaussian grid fit"
            row["classification_scope"] = "stimulus-response RF reliability, not Dm8 identity"
        selected.extend(fly_rows)
        mask = np.array([row["rf_classification"] == "RF_RELIABLE" for row in fly_rows])
        result = computed[item.fly_id, rf_kind]
        kernels = result["kernel_full_zscore"].reshape(phase5.feature.bins, 15, 15, -1)
        centers = result["center"]
        within_before = within_after = None
        temporal_peak = None
        if np.any(mask):
            normalized = kernels[:, :, :, mask].copy()
            for roi in range(normalized.shape[-1]):
                spatial = result["spatial"][:, :, np.flatnonzero(mask)[roi]]
                peak = np.unravel_index(np.argmax(np.abs(spatial)), spatial.shape)
                if kernels[result["dominant_bin"][np.flatnonzero(mask)[roi]], peak[0], peak[1],
                           np.flatnonzero(mask)[roi]] < 0:
                    normalized[:, :, :, roi] *= -1
            aligned = align_kernels(normalized, centers[mask])
            if mask.sum() >= 2:
                dominant = result["dominant_bin"][mask]
                before_spatial = np.stack([normalized[dominant[i], :, :, i]
                                           for i in range(normalized.shape[-1])], axis=2)
                after_spatial = np.stack([aligned[dominant[i], :, :, i]
                                          for i in range(aligned.shape[-1])], axis=2)
                within_before = pairwise_spatial_similarity(before_spatial)["all"]
                within_after = pairwise_spatial_similarity(after_spatial)["all"]
            selected_kernels.append(normalized)
            selected_centers.append(centers[mask])
            selected_groups.extend([item.fly_id] * int(mask.sum()))
            mean_rf = aligned.mean(axis=3)
            temporal_peak = int(np.argmax(np.abs(mean_rf[:, 7, 7])))
        else:
            mean_rf = np.full((phase5.feature.bins, 15, 15), np.nan)
        mean_path = align_dir / f"{item.fly_id}_center_aligned_mean_rf.npz"
        np.savez_compressed(mean_path, mean_rf=mean_rf.astype(np.float32),
                            has_reliable_rf=bool(np.any(mask)),
                            reliable_roi_labels=np.asarray(item.roi_labels)[mask],
                            centers=centers[mask])
        fly_mean_paths.append(mean_path)
        fly_mean_paths.append(save_csv(align_dir / f"{item.fly_id}_center_map.csv", fly_rows))
        distances = [row["split_half_center_distance"] for row in fly_rows
                     if row["rf_classification"] == "RF_RELIABLE" and
                     row["split_half_center_distance"] is not None]
        fly_summaries.append({"fly_id": item.fly_id, "total_roi": len(item.roi_labels),
                              "rf_reliable": int(mask.sum()),
                              "center_aligned_temporal_peak_bin": temporal_peak,
                              "cross_roi_similarity_before_alignment": within_before,
                              "cross_roi_similarity_after_alignment": within_after,
                              "median_reliable_split_half_rf_r": _finite(np.median([
                                  row["split_half_rf_r"] for row in fly_rows if
                                  row["rf_classification"] == "RF_RELIABLE"])) if np.any(mask) else None,
                              "median_reliable_center_displacement": float(np.median(distances))
                              if distances else None})

    reliable = [row for row in selected if row["rf_classification"] == "RF_RELIABLE"]
    valid_centers = np.array([(row["center_row"], row["center_col"]) for row in selected
                              if row["valid_trace"] and row["center_row"] is not None and
                              row["center_col"] is not None], dtype=float).reshape(-1, 2)
    reliable_centers = np.array([(row["center_row"], row["center_col"]) for row in reliable],
                                dtype=float).reshape(-1, 2)
    def center_histogram(centers: np.ndarray) -> list[list[int]]:
        return np.histogram2d(centers[:, 0], centers[:, 1],
                              bins=(np.arange(16) - .5, np.arange(16) - .5))[0].astype(int).tolist()
    displacement = np.array([row["split_half_center_distance"] for row in reliable], dtype=float)
    gate_a = sum(row["rf_reliable"] >= config["gate_min_reliable_per_fly"]
                 for row in fly_summaries) >= config["gate_min_flies"]
    gate_b = (len(displacement) >= 10 and
              np.median(displacement) <= config["gate_max_median_center_displacement_pixels"] and
              np.quantile(displacement, .75) <= config["gate_max_p75_center_displacement_pixels"])
    before = after = None
    cross_path = align_dir / "cross_fly_center_aligned_rf.npz"
    if selected_kernels:
        all_kernels = np.concatenate(selected_kernels, axis=3)
        all_centers = np.concatenate(selected_centers)
        aligned = align_kernels(all_kernels, all_centers)
        # Use the same dominant temporal bin for each ROI before and after shift.
        dominant = np.argmax(np.sum(all_kernels ** 2, axis=(1, 2)), axis=0)
        original_spatial = np.stack([all_kernels[dominant[i], :, :, i]
                                     for i in range(all_kernels.shape[3])], axis=2)
        aligned_spatial = np.stack([aligned[dominant[i], :, :, i]
                                    for i in range(aligned.shape[3])], axis=2)
        groups = np.asarray(selected_groups)
        before = pairwise_spatial_similarity(original_spatial, groups)
        after = pairwise_spatial_similarity(aligned_spatial, groups)
        np.savez_compressed(cross_path,
                            mean_rf=aligned.mean(axis=3).astype(np.float32),
                            fly_ids=groups, centers=all_centers,
                            aligned_kernels=aligned.astype(np.float32))
    else:
        np.savez_compressed(cross_path,
                            mean_rf=np.full((phase5.feature.bins, 15, 15), np.nan, dtype=np.float32),
                            has_reliable_rf=False,
                            fly_ids=np.asarray([], dtype="U1"),
                            centers=np.empty((0, 2)),
                            aligned_kernels=np.empty((phase5.feature.bins, 15, 15, 0), dtype=np.float32))

    selected_path = save_csv(align_dir / "roi_rf_classification.csv", selected)
    fly_path = save_csv(align_dir / "fly_rf_summary.csv", fly_summaries)
    alignment = save_json(align_dir / "phase6_gate.json", {
        "selected_rf_representation": rf_kind,
        "selected_future_predictive_representation": predictive_kind,
        "reliable_roi_count": len(reliable), "fly_summary": fly_summaries,
        "reliable_split_half_rf_r": [row["split_half_rf_r"] for row in reliable],
        "reliable_split_half_center_displacement": displacement.tolist(),
        "center_distribution_reliable_15x15": center_histogram(reliable_centers),
        "center_distribution_all_valid_descriptive_15x15": center_histogram(valid_centers),
        "median_reliable_center_displacement": _finite(np.median(displacement)) if len(displacement) else None,
        "p75_reliable_center_displacement": _finite(np.quantile(displacement, .75)) if len(displacement) else None,
        "pairwise_spatial_similarity_before_alignment": before,
        "pairwise_spatial_similarity_after_alignment": after,
        "gate_a_reliable_across_flies": bool(gate_a),
        "gate_b_stable_centers": bool(gate_b),
        "gate_c_li_gain_over_raw": bool(
            scores["li_style_rf_relative"]["fly_balanced_train_rf_score"] -
            scores["raw"]["fly_balanced_train_rf_score"] >= config["representation_clear_gain"]),
        "gate_c_causal_gain_over_raw": bool(
            max(scores[kind]["fly_balanced_train_rf_score"] for kind in
                ("causal_ema_residual_60s", "causal_block_median_residual_60s")) -
            scores["raw"]["fly_balanced_train_rf_score"] >= config["representation_clear_gain"]),
        "recommend_phase6_2": bool(gate_a and gate_b),
        "test_response_accessed": False,
        "gate_rule": config})
    align_outputs = [selected_path, fly_path, alignment, *fly_mean_paths, cross_path]
    return write_stage_manifest("phase_06_1C_rf_center_alignment", align_dir, config,
        [rf_manifest, *rf_outputs], align_outputs, root,
        details={"rf_reliable": len(reliable), "gate_a": bool(gate_a),
                 "gate_b": bool(gate_b), "recommend_phase6_2": bool(gate_a and gate_b)})
