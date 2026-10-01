"""Reproduce the fixed graduation analysis directly from immutable saved sources."""

import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dm8_modeling.data import load_recordings, source_manifest, manifest_digest, sha256
from dm8_modeling.rf import estimate_strf, global_energy_lag, zone_means
from dm8_modeling.population import fly_spatial, population_spatial, temporal_maps
from dm8_modeling.models import projection_matrix, rotational_profile, fit_models
from dm8_modeling.statistics import full_pipeline_null
from dm8_modeling.plotting import final_figures


def check_regression(actual: dict, config: dict) -> dict:
    """Compare only declared frozen-data numbers; changed data need explicit rebaselining."""
    expected = config.get("numerical_regression", {})
    tolerance = expected.get("absolute_tolerance", 1e-6)
    checks = {}
    for key, value in actual.items():
        if key in expected:
            difference = abs(value-expected[key])
            checks[key] = {"actual": value, "expected": expected[key], "absolute_error": difference,
                           "passed": bool(np.isfinite(value) and difference <= tolerance)}
    if any(not item["passed"] for item in checks.values()):
        raise RuntimeError(f"Numerical regression failed; preserve historical files: {checks}")
    return checks


def write_table(path: Path, rows: list[dict]) -> None:
    """Save one final numerical CSV with explicit column names and no dataframe index."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(config_path: Path) -> dict:
    """One source→RF→fly→population→model→500-null pipeline; no old result inputs."""
    config = json.loads(config_path.read_text())
    config_hash = sha256(config_path)
    root = config_path.resolve().parents[1]
    sources = {name: (root/name).resolve() for name in config["protected_source_roots"]}
    output = (root/config["output_root"]).resolve()
    if any(output == path or output.is_relative_to(path) or path.is_relative_to(output) for path in sources.values()):
        raise ValueError("Output directory must not overlap protected sources")
    if config["native_lags"] != 40 or config["grid_size"] != 15:
        raise ValueError("The frozen final definition requires 40 native lags and 15×15 pixels")
    conventions = {
        "schema_version": "dm8_final_analysis_v1",
        "gaussian_edge_policy": "reflect_then_trim_3sigma_for_primary_spatial_RF",
        "rf_normalization": "full_STRF_zscore_per_ROI_after_covariance",
        "spatial_extraction": "one_global_full_record_energy_peak_lag",
        "center_method": "spatial_zscore_abs_peak_signed_axis_gaussian",
        "alignment": "bilinear_valid_support_nan_padding_no_wrap",
        "weighting": "equal_ROI_within_fly_then_equal_fly"}
    if any(config.get(key) != value for key, value in conventions.items()):
        raise ValueError("Unsupported method convention: the final runner has one scientific estimator")
    diagnostic = config["temporal_diagnostic"]
    if (diagnostic["segment"] != "full_eligible_payload"
            or diagnostic["reference_center"] != "dominant_4x10_raw_covariance_reference_kernel"
            or diagnostic["alignment"] != "rounded_integer_nan_padding_no_wrap"
            or diagnostic["candidate_lag"] != 4
            or config["gaussian_truncate_sigma"] != 3):
        raise ValueError("Unsupported temporal diagnostic or edge definition")
    print("Fingerprinting protected sources and loading saved stimulus/TTL/ROI files", flush=True)
    before = source_manifest(sources)
    recordings = load_recordings((root/config["data_root"]).resolve(), config)
    full = [estimate_strf(recording, config, trim=False) for recording in recordings]
    lag = global_energy_lag(full)
    trimmed = [estimate_strf(recording, config, trim=True) for recording in recordings]
    flies = [fly_spatial(item, lag, config) for item in trimmed]
    population = population_spatial(flies)
    observed = zone_means(population["map"], config)
    print(f"Primary spatial RF: lag {lag}, center {observed[0]:.12f}, surround {observed[1]:.12f}", flush=True)
    fly_temporal, population_temporal = temporal_maps(full, config)
    temporal = []
    for index in range(config["native_lags"]):
        for recording, image in zip(recordings, fly_temporal[:, index], strict=True):
            center, surround = zone_means(image, config)
            temporal.append({"lag": index, "fly": recording.fly, "center": center, "surround": surround})
        center, surround = zone_means(population_temporal[index], config)
        temporal.append({"lag": index, "fly": "population", "center": center, "surround": surround})
    projector = projection_matrix(config["grid_size"], config["projection_rotation_steps"])
    models = []
    for name, image in [(r.fly, f["map"]) for r, f in zip(recordings, flies, strict=True)] + [("population", population["map"])]:
        models.extend({"unit": name, **fit} for fit in fit_models(rotational_profile(image, projector), config))
    population_models = {fit["model"]: fit for fit in models if fit["unit"] == "population"}
    candidate_lag = config["temporal_diagnostic"]["candidate_lag"]
    metrics = {"negative_center_flies": sum(zone_means(f["map"], config)[0] < 0 for f in flies),
        "spatial_center": observed[0], "spatial_surround": observed[1],
        "temporal_lag1_center": zone_means(population_temporal[1], config)[0],
        "temporal_lag4_surround": zone_means(population_temporal[candidate_lag], config)[1],
        "temporal_lag4_positive_flies": sum(zone_means(image, config)[1] > 0 for image in fly_temporal[:, candidate_lag]),
        "gaussian_r2": population_models["M1"]["r2"], "gaussian_aicc": population_models["M1"]["aicc"],
        "dog_aicc": population_models["M3"]["aicc"]}
    checks = check_regression(metrics, config)
    print(f"Spatial, temporal and model numerical checks passed: {metrics}", flush=True)
    null_summary, null_values = full_pipeline_null(recordings, config, observed)
    metrics.update({key: null_summary[key] for key in ("center_p_negative", "surround_p_positive")})
    checks = check_regression(metrics, config)
    after = source_manifest(sources)
    if before != after:
        raise RuntimeError("Protected source files changed during analysis")
    if sha256(config_path) != config_hash:
        raise RuntimeError("Configuration changed during analysis")
    dataset, fly_rows = [], []
    for recording, estimate, untrimmed, fly in zip(recordings, trimmed, full, flies, strict=True):
        meta = recording.metadata
        dataset.append({"fly": recording.fly, "run_id": recording.run_id, "total_roi": meta["total_roi"],
            "technical_roi": meta["technical_roi"], "aligned_roi": fly["aligned_roi"],
            "payload_frames": len(recording.response), "full_rf_frames": untrimmed["frames"], "trimmed_rf_frames": estimate["frames"],
            "stimulus_updates": len(recording.stimulus), "grid_size": config["grid_size"],
            "imaging_hz": 1e6/meta["median_imaging_interval_us"], "update_hz": 1e6/meta["median_update_interval_us"],
            "digital_dark": meta["digital_dark"], "digital_bright": meta["digital_bright"], "frozen_seed": meta["seed"]})
        centers = fly["centers"]
        finite = np.isfinite(centers).all(axis=1)
        edge = np.min(np.column_stack((centers[finite], config["grid_size"]-1-centers[finite])), axis=1)
        center, surround = zone_means(fly["map"], config)
        roi_zones = [zone_means(fly["roi_maps"][:, :, i], config)[0] for i in np.flatnonzero(finite)]
        fly_rows.append({"fly": recording.fly, "center": center, "surround": surround,
            "technical_roi": meta["technical_roi"], "aligned_roi": fly["aligned_roi"],
            "negative_center_roi_fraction": float(np.mean(np.asarray(roi_zones) < 0)),
            "median_center_row_px": float(np.nanmedian(centers[:, 0])), "median_center_col_px": float(np.nanmedian(centers[:, 1])),
            "fraction_center_within_3px_of_edge": float(np.mean(edge < 3)), "rf_frames": estimate["frames"]})
    summary = {"schema_version": config["schema_version"], "config_sha256": config_hash,
        "pre_cleanup_head": config["pre_cleanup_head"], "dataset": dataset,
        "source_metadata": {r.fly: {k: v for k, v in r.metadata.items() if k != "source_rows_zero_based"} for r in recordings},
        "spatial": {"global_energy_peak_lag": lag, **{k: metrics[k] for k in ("negative_center_flies", "spatial_center", "spatial_surround")},
            "population_map": population["map"].tolist(), "fly_maps": [f["map"].tolist() for f in flies],
            "roi_support": population["roi_support"].tolist(), "fly_support": population["fly_support"].tolist()},
        "temporal": {"definition": config["temporal_diagnostic"], **{k: metrics[k] for k in (
            "temporal_lag1_center", "temporal_lag4_surround", "temporal_lag4_positive_flies")}},
        "models": models, "statistics": {**null_summary, "sample_columns": ["center", "surround"],
            "samples": null_values.tolist()}, "numerical_regression": checks,
        "source_integrity": {"files": len(before), "sha256_before": manifest_digest(before), "sha256_after": manifest_digest(after), "unchanged": True},
        "interpretation": "Stimulus-linked negative fluorescence RF center; broad conserved positive surround unsupported; lag4 is post-hoc."}
    output.mkdir(parents=True, exist_ok=True)
    tables = output/"tables"
    tables.mkdir(exist_ok=True)
    write_table(tables/"dataset_summary.csv", dataset)
    write_table(tables/"fly_rf_summary.csv", fly_rows)
    write_table(tables/"temporal_rf_summary.csv", temporal)
    write_table(tables/"model_comparison.csv", [{k: v for k, v in fit.items() if k not in ("prediction", "fit_positions_px")} for fit in models])
    write_table(tables/"null_summary.csv", [{"zone": zone, "observed": null_summary[f"observed_{zone}"],
        "empirical_p_one_sided": null_summary["center_p_negative" if zone == "center" else "surround_p_positive"],
        "tail": "negative" if zone == "center" else "positive", "iterations": len(null_values),
        "seed": config["null_seed"], "q025": null_summary[f"{zone}_null_quantiles"][0],
        "q50": null_summary[f"{zone}_null_quantiles"][1], "q975": null_summary[f"{zone}_null_quantiles"][2]} for zone in ("center", "surround")])
    final_figures(output/"figures", flies, population, temporal, models, projector, null_values, null_summary, config)
    (output/"final_results.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    (output/"source_hashes.json").write_text(json.dumps(before, indent=2, sort_keys=True)+"\n")
    print(f"Complete: 5 tables, 7 figures, {len(checks)} numerical checks; {len(before)} source hashes unchanged", flush=True)
    return summary


def main() -> None:
    """Read the sole config path and execute the reproducible final analysis."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1]/"configs/final_analysis.json")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
