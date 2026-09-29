"""Reproducible first-round five-fly experiment matrix.

Hyperparameters and ROI membership are frozen from TRAIN/VALIDATION; TEST is
read only for final scoring. A fly is one biological unit despite many ROIs
and all five recordings sharing the same digital stimulus sequence.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from ..datasets import build_integrated_dataset, build_population_dataset, load_individual_datasets, write_integrated_manifest
from ..datasets.splits import TEST, TRAIN
from ..evaluation.cross_fly import leave_one_fly_out
from ..evaluation.comparison import write_cross_fold_comparison
from ..evaluation.metrics import score_columns, summarize_roi_records
from ..evaluation.plots import write_dataset_diagnostics, write_fly_scores, write_model_comparison, write_population_scores
from ..evaluation.reliability import assess_training_reliability
from ..models.linear.individual import fit_individual_pixel, fit_individual_ridge
from ..models.population.hierarchical_strf import fit_hierarchical_strf
from ..models.population.population_average import fit_population_average
from ..models.population.shared_basis import fit_shared_basis
from ..models.population.shared_strf import fit_shared_strf
from ..preprocessing.normalization import process_individual_response
from .config import Phase5Config
from .registry import write_registry


def _number(value):
    value = float(value)
    return value if np.isfinite(value) else None


def _git_revision(path: Path) -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=path, text=True).strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _score_fit(fold, fit, individuals, processed, selected, baseline=None) -> tuple[list[dict], dict]:
    records = []
    for item in individuals:
        test = item.split_label == TEST
        y = processed[item.fly_id].values
        train_var = np.var(y[item.split_label == TRAIN].astype(np.float64), axis=0)
        metrics = score_columns(y[test], fit.predictions[item.fly_id][test], train_var)
        for roi, label in enumerate(item.roi_labels):
            records.append({"fold": fold, "model": fit.name, "fly_id": item.fly_id,
                            "run_id": item.run_id, "roi_id": label,
                            "train_defined_responsive": bool(selected[item.fly_id][roi]),
                            **{key: _number(values[roi]) for key, values in metrics.items()}})
    return records, summarize_roi_records(records, baseline)


def _write_model_artifacts(path: Path, fit, records: list[dict], summary: dict,
                           config: Phase5Config, individuals, details: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _write_csv(path / "roi_test_metrics.csv", records)
    _write_csv(path / "metrics.csv", records)
    (path / "config.json").write_text(json.dumps(config.raw, indent=2, ensure_ascii=False) + "\n")
    (path / "source_hashes.json").write_text(json.dumps({item.fly_id: item.aligned.qc["source_sha256"]
        for item in individuals}, indent=2) + "\n")
    commit, git_dirty = _git_revision(path)
    payload = {"schema_version": "phase5_model_v1", "model": fit.name,
               "response_kind": details["response_kind"], "normalization": details["normalization"],
               "summary": summary, "selection": details["selection"],
               "git_commit_at_run": commit, "git_worktree_dirty_at_run": git_dirty,
               "random_seed": config.raw["random_seed"],
               "data_limit": "One frozen stimulus sequence across five flies; raw Results.csv ROI mean intensity is not verified calcium DeltaF/F."}
    (path / "summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_fly_scores(path / "per_fly_test_r2.svg", fit.name, summary)
    # Compact interpretable parameters; predictions and raw data are not duplicated.
    parameters = {}
    if hasattr(fit, "parameters"):
        for fly, values in fit.parameters.items():
            for key, value in values.items():
                parameters[f"{fly}__{key}"] = np.asarray(value)
    if hasattr(fit, "core"):
        parameters["shared_kernel"] = fit.core.kernel
        for fly in fit.core.gains:
            parameters[f"{fly}__gain"] = fit.core.gains[fly]
            parameters[f"{fly}__bias"] = fit.core.biases[fly]
    if hasattr(fit, "fly_deviation"):
        parameters["shared_kernel"] = fit.shared_core.kernel
        for fly, deviation in fit.fly_deviation.items():
            parameters[f"{fly}__deviation"] = deviation
    if hasattr(fit, "basis"):
        parameters.update(basis=fit.basis, temporal=fit.temporal_components, spatial=fit.spatial_components)
        for fly in fit.heads:
            parameters[f"{fly}__head"] = fit.heads[fly]
            parameters[f"{fly}__intercept"] = fit.intercepts[fly]
    if hasattr(fit, "ridge"):
        parameters.update(coefficient=fit.ridge.coefficient, intercept=fit.ridge.intercept)
    np.savez_compressed(path / "model_parameters.npz", **parameters)
    (path / "run.log").write_text(json.dumps({"completed_unix_time": time.time(),
        "fold": details["fold"], "model": fit.name, "roi_count": summary["roi_count"]}) + "\n")


def run_first_round(config_path: Path, data_root: Path, output_root: Path,
                    model_filter: set[str] | None = None) -> dict:
    """Run the configured matrix and persist scores plus full provenance.

    A filter limits compute for a CLI fit, but selection/test logic is shared.
    """
    config = Phase5Config.load(config_path)
    output_root.mkdir(parents=True, exist_ok=True)
    registry_rows: list[dict] = []
    final = {"schema_version": "phase5_first_round_v1", "folds": {},
             "config_path": str(config_path.resolve()), "model_filter": sorted(model_filter) if model_filter else None}
    for fold in config.folds:
        print(f"Phase 5 {fold.name}: loading and aligning five flies", flush=True)
        individuals = load_individual_datasets(data_root, config.feature, fold)
        fold_root = output_root / fold.name
        fold_root.mkdir(parents=True, exist_ok=True)
        integrated = build_integrated_dataset(individuals)
        write_integrated_manifest(integrated, fold_root / "dataset", {"feature": config.raw["feature"],
                                  "split": fold.intervals()})
        provenance = integrated.explain_row(0)
        (fold_root / "dataset" / "example_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
        del integrated
        processed = {item.fly_id: process_individual_response(item, "raw", "train_zscore") for item in individuals}
        reliability = {item.fly_id: assess_training_reliability(item, processed[item.fly_id]) for item in individuals}
        selected = {fly: result.selected for fly, result in reliability.items()}
        _write_csv(fold_root / "roi_reliability.csv", [record for result in reliability.values()
                                                       for record in result.records()])
        write_dataset_diagnostics(fold_root / "dataset" / "dataset_diagnostics.svg",
                                  individuals, processed, reliability, fold)
        print(f"{fold.name}: selected {sum(int(mask.sum()) for mask in selected.values())}/"
              f"{sum(len(mask) for mask in selected.values())} training-responsive ROIs", flush=True)
        alphas = tuple(config.raw["model"]["ridge_alphas"])
        outputs: dict[str, dict] = {}
        baseline = None

        def save(fit, responses, kind="raw", normalization="train_zscore", extra=None):
            nonlocal baseline
            name = fit.name if normalization == "train_zscore" or fit.name.endswith("raw_units") else f"{fit.name}__raw_units"
            fit_path = fold_root / "models" / name
            records, summary = _score_fit(fold.name, fit, individuals, responses, selected,
                                          baseline if kind == "raw" else None)
            detail = {"fold": fold.name, "response_kind": kind, "normalization": normalization,
                      "selection": extra or {}}
            _write_model_artifacts(fit_path, fit, records, summary, config, individuals, detail)
            outputs[name] = summary
            registry_rows.append({"experiment_id": f"phase5_{fold.name}_{name}", "fold": fold.name,
                "date_utc": datetime.now(timezone.utc).isoformat(),
                "dataset": "five_fly_one_frozen_stimulus", "hyperparameters": json.dumps(extra or {}),
                "model": name, "response_kind": kind, "normalization": normalization,
                "roi_count": summary["roi_count"], "all_roi_median_r2": summary["all_roi_median_r2"],
                "responsive_median_r2": summary["train_defined_responsive_median_r2"],
                "fraction_positive_r2": summary["all_roi_positive_r2_fraction"],
                "comparison_baseline": ("individual_ridge__raw_units" if normalization == "raw" else
                                        "individual_ridge" if kind == "raw" else
                                        "individual_ridge_validation_selected_response"),
                "notes": "historical exploratory test; one common frozen stimulus",
                "artifact_dir": str(fit_path.resolve())})
            if name == "individual_ridge":
                baseline = {(row["fly_id"], row["roi_id"]): row["r2"] for row in records}
            print(f"{fold.name} {name}: median TEST R2={summary['all_roi_median_r2']}", flush=True)

        # Both baselines use the exact same causal X and global intervals.
        if model_filter is None or "individual_pixel" in model_filter:
            save(fit_individual_pixel(individuals, processed, alphas), processed)
        ridge_fit = fit_individual_ridge(individuals, processed, alphas)
        if model_filter is None or "individual_ridge" in model_filter:
            save(ridge_fit, processed)
        if model_filter is None or "individual_raw_units" in model_filter:
            raw = {item.fly_id: process_individual_response(item, "raw", "raw") for item in individuals}
            save(fit_individual_ridge(individuals, raw, alphas), raw, normalization="raw")

        shared = None
        if model_filter is None or any(name in model_filter for name in
               ("shared_strf_affine", "shared_plus_fly_deviation")):
            shared = fit_shared_strf(individuals, processed, tuple(config.raw["model"]["shared_alphas"]),
                iterations=config.raw["model"]["shared_iterations"],
                loss_weighting=config.raw["model"]["loss_weighting"])
            if model_filter is None or "shared_strf_affine" in model_filter:
                save(shared, processed, extra={"validation_candidates": shared.validation_candidates,
                     "selected_alpha": shared.core.alpha})
        if shared is not None and (model_filter is None or "shared_plus_fly_deviation" in model_filter):
            hierarchical = fit_hierarchical_strf(individuals, processed, shared,
                tuple(config.raw["model"]["fly_penalties"]), config.raw["model"]["shared_iterations"])
            save(hierarchical, processed, extra={"validation_candidates": hierarchical.validation_candidates,
                                                       "selected_penalty": hierarchical.lambda_fly})
        if model_filter is None or "shared_strf_equal_roi" in model_filter:
            equal_roi = fit_shared_strf(individuals, processed,
                tuple(config.raw["model"]["shared_alphas"]),
                iterations=config.raw["model"]["shared_iterations"], loss_weighting="equal_roi")
            equal_roi = type(equal_roi)("shared_strf_equal_roi", equal_roi.core, equal_roi.predictions,
                                        equal_roi.validation_median_r2, equal_roi.validation_candidates)
            save(equal_roi, processed, extra={"validation_candidates": equal_roi.validation_candidates,
                                                 "loss_weighting": "equal_roi"})
        if model_filter is None or "shared_strf_raw_units" in model_filter:
            raw = {item.fly_id: process_individual_response(item, "raw", "raw") for item in individuals}
            raw_shared = fit_shared_strf(individuals, raw,
                tuple(config.raw["model"]["shared_alphas"]),
                iterations=config.raw["model"]["shared_iterations"])
            raw_shared = type(raw_shared)("shared_strf_raw_units", raw_shared.core,
                                          raw_shared.predictions, raw_shared.validation_median_r2,
                                          raw_shared.validation_candidates)
            save(raw_shared, raw, normalization="raw", extra={"validation_candidates": raw_shared.validation_candidates})
        if model_filter is None or "shared_factorized_basis" in model_filter:
            basis = fit_shared_basis(individuals, processed, ridge_fit,
                tuple(config.raw["model"]["basis_counts"]),
                tuple(config.raw["model"]["basis_head_alphas"]))
            save(basis, processed, extra={"validation_candidates": basis.validation_candidates,
                                          "selected_rank": basis.basis_count,
                                          "selected_head_alpha": basis.head_alpha})
        if model_filter is None or "population_average_ridge" in model_filter:
            populations = {item.fly_id: build_population_dataset(item, processed[item.fly_id],
                            reliability[item.fly_id]) for item in individuals}
            population_fit = fit_population_average(individuals, populations, alphas)
            rows = []
            for item in individuals:
                target = populations[item.fly_id].response
                test = item.split_label == TEST
                variance = np.asarray([np.var(target[item.split_label == TRAIN])])
                scores = score_columns(target[test, None], population_fit.predictions[item.fly_id][test, None], variance)
                rows.append({"fly_id": item.fly_id, "member_count": len(populations[item.fly_id].roi_membership),
                             **{key: _number(value[0]) for key, value in scores.items()}})
            path = fold_root / "models" / "population_average_ridge"
            path.mkdir(parents=True, exist_ok=True)
            _write_csv(path / "population_test_metrics.csv", rows)
            _write_csv(path / "metrics.csv", rows)
            (path / "members.json").write_text(json.dumps({fly: list(pop.roi_membership)
                for fly, pop in populations.items()}, indent=2) + "\n")
            commit, git_dirty = _git_revision(path)
            (path / "summary.json").write_text(json.dumps({"model": population_fit.name,
                "median_test_r2_across_five_flies": _number(np.median([row["r2"] for row in rows])),
                "validation_candidates": population_fit.validation_candidates,
                "target": "within-fly mean of training-selected standardized ROI intensity",
                "git_commit_at_run": commit,
                "git_worktree_dirty_at_run": git_dirty}, indent=2) + "\n")
            np.savez_compressed(path / "model_parameters.npz", coefficient=population_fit.ridge.coefficient,
                                intercept=population_fit.ridge.intercept)
            (path / "config.json").write_text(json.dumps(config.raw, indent=2) + "\n")
            (path / "source_hashes.json").write_text(json.dumps({item.fly_id: item.aligned.qc["source_sha256"]
                for item in individuals}, indent=2) + "\n")
            (path / "run.log").write_text(json.dumps({"completed_unix_time": time.time(),
                "fold": fold.name, "model": population_fit.name, "target": "population_average"}) + "\n")
            write_population_scores(path / "per_fly_test_r2.svg", rows)
            outputs["population_average_ridge"] = json.loads((path / "summary.json").read_text())
            registry_rows.append({"experiment_id": f"phase5_{fold.name}_population_average_ridge",
                "date_utc": datetime.now(timezone.utc).isoformat(), "dataset": "five_fly_one_frozen_stimulus",
                "fold": fold.name, "model": population_fit.name, "response_kind": "raw",
                "normalization": "train_zscore", "roi_count": 5,
                "hyperparameters": json.dumps({"validation_candidates": population_fit.validation_candidates}),
                "all_roi_median_r2": outputs["population_average_ridge"]["median_test_r2_across_five_flies"],
                "responsive_median_r2": "", "fraction_positive_r2": float(np.mean([row["r2"] > 0 for row in rows])),
                "comparison_baseline": "none_same_target", "notes": "population target differs from per-ROI target",
                "artifact_dir": str(path.resolve())})

        # Candidate response transforms are compared using VALIDATION only.
        if model_filter is None or "response_candidates" in model_filter:
            candidate_rows = []
            for kind in config.raw["response"]["candidate_kinds"]:
                values = {item.fly_id: process_individual_response(item, kind, "train_zscore") for item in individuals}
                trial = fit_shared_strf(individuals, values, tuple(config.raw["model"]["shared_alphas"]),
                    iterations=config.raw["model"]["shared_iterations"])
                candidate_rows.append({"response_kind": kind,
                    "shared_validation_median_r2": _number(trial.validation_median_r2),
                    "selected_alpha": trial.core.alpha})
                print(f"{fold.name} preprocessing {kind}: validation R2={trial.validation_median_r2}", flush=True)
            _write_csv(fold_root / "response_candidate_validation.csv", candidate_rows)
            outputs["response_candidates"] = candidate_rows
            best_kind = max(candidate_rows, key=lambda row: row["shared_validation_median_r2"])["response_kind"]
            candidate_processed = {item.fly_id: process_individual_response(item, best_kind, "train_zscore")
                                   for item in individuals}
            candidate_shared = fit_shared_strf(individuals, candidate_processed,
                tuple(config.raw["model"]["shared_alphas"]),
                iterations=config.raw["model"]["shared_iterations"])
            candidate_shared = type(candidate_shared)("shared_strf_validation_selected_response",
                candidate_shared.core, candidate_shared.predictions,
                candidate_shared.validation_median_r2, candidate_shared.validation_candidates)
            save(candidate_shared, candidate_processed, kind=best_kind,
                 extra={"response_selected_from": "validation_only", "validation_candidates": candidate_rows})
            candidate_ridge = fit_individual_ridge(individuals, candidate_processed, alphas)
            candidate_ridge = type(candidate_ridge)("individual_ridge_validation_selected_response",
                candidate_ridge.predictions, candidate_ridge.parameters,
                candidate_ridge.validation_median_r2)
            save(candidate_ridge, candidate_processed, kind=best_kind,
                 extra={"response_selected_from": "validation_only", "validation_candidates": candidate_rows})

        if model_filter is None or "leave_one_fly_out" in model_filter:
            transfer = leave_one_fly_out(individuals, processed,
                tuple(config.raw["model"]["shared_alphas"]),
                config.raw["transfer"]["few_shot_fraction"], config.raw["model"]["shared_iterations"])
            for row in transfer:
                for key in ("pearson_r", "r2", "mse", "normalized_mse"):
                    row[key] = _number(row[key])
            _write_csv(fold_root / "leave_one_fly_out.csv", transfer)
            outputs["leave_one_fly_out"] = {mode: _number(np.nanmedian([row["r2"] for row in transfer
                if row["mode"] == mode and row["r2"] is not None])) for mode in ("zero_shot", "few_shot_readout")}
        final["folds"][fold.name] = outputs
        write_model_comparison(fold_root / "model_comparison.svg", fold.name, outputs)
        (fold_root / "fold_summary.json").write_text(json.dumps(outputs, indent=2, allow_nan=False) + "\n")
    write_registry(registry_rows, output_root / "experiment_registry.csv")
    if model_filter is None:
        final["cross_fold_comparison"] = write_cross_fold_comparison(output_root)
    (output_root / "first_round_summary.json").write_text(json.dumps(final, indent=2, allow_nan=False) + "\n")
    return final
