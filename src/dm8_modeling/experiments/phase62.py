"""Phase 6.2 full-recording descriptive RF, with fly as biological unit."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ..data import align_session, discover_sessions
from ..features.temporal_basis import binned_design
from ..io.stage_manifest import write_stage_manifest
from ..io.tables import save_csv, save_json
from ..preprocessing.rf_response import li_style_relative_response
from ..rf.characterization import reverse_correlation, rf_maps
from ..rf.population import (dog_gate, energy_centers, fit_radial_dog, image_correlation,
                             pairwise_median, radial_profile, shift_to_center, valid_mean,
                             zone_means)
from .workflow import WorkflowContext


def _finite(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _stacked_kernels(design: np.ndarray, response: np.ndarray, bins: int) -> tuple[np.ndarray, dict]:
    """Return signed RF in standardized-response units and center diagnostics."""
    kernel = reverse_correlation(design, response).reshape(bins, 15, 15, -1)
    return kernel, rf_maps(kernel.reshape(bins * 225, -1), bins)


def _one_fly(aligned, config: dict, out: Path) -> tuple[dict, list[dict], np.ndarray, np.ndarray, np.ndarray, np.ndarray, Path]:
    bins, width = config["temporal_bins"], config["updates_per_bin"]
    history = bins * width
    eligible = aligned.update_index >= history - 1
    raw = aligned.response
    n_roi = raw.shape[1]
    zero = np.mean(raw == 0, axis=0)
    finite = np.isfinite(raw).all(axis=0)
    raw_std = np.std(np.where(np.isfinite(raw), raw, 0), axis=0)
    technical = finite & (zero < config["max_raw_zero_fraction"]) & (raw_std > config["minimum_response_std"])
    selected = np.flatnonzero(technical)
    if not len(selected):
        raise ValueError(f"No technically valid ROI for {aligned.session.fly}")
    li_full, edge_margin = li_style_relative_response(
        raw[:, selected], aligned.imaging_time_us, config["gaussian_sigma_seconds"],
        config["gaussian_truncate_sigma"])
    li = li_full[eligible]
    raw_selected = raw[eligible][:, selected]
    li_std = np.std(li, axis=0)
    remaining = li_std > config["minimum_response_std"]
    selected = selected[remaining]
    li, raw_selected = li[:, remaining], raw_selected[:, remaining]
    li_std = li_std[remaining]
    if not len(selected):
        raise ValueError(f"No valid Li-style response for {aligned.session.fly}")
    design = binned_design(aligned.stimulus, aligned.update_index[eligible], bins, width)
    li_scaled = ((li - li.mean(axis=0)) / li_std).astype(np.float32)
    raw_scaled = ((raw_selected - raw_selected.mean(axis=0)) /
                  raw_selected.std(axis=0)).astype(np.float32)
    kernel, maps = _stacked_kernels(design, li_scaled, bins)
    raw_kernel, _ = _stacked_kernels(design, raw_scaled, bins)
    midpoint = len(design) // 2
    _, first_maps = _stacked_kernels(design[:midpoint], li_scaled[:midpoint], bins)
    _, second_maps = _stacked_kernels(design[midpoint:], li_scaled[midpoint:], bins)
    split_distance = np.linalg.norm(first_maps["centers"] - second_maps["centers"], axis=1)
    primary_center = maps["centers"]
    centroid = energy_centers(kernel)
    original = np.full((15, 15, n_roi), np.nan)
    raw_original = np.full_like(original, np.nan)
    center = np.full((n_roi, 2), np.nan)
    centroid_full = np.full_like(center, np.nan)
    center_distance = np.full(n_roi, np.nan)
    center_quality = np.full(n_roi, np.nan)
    full_kernel = np.full((bins, 15, 15, n_roi), np.nan, dtype=np.float32)
    for column, roi in enumerate(selected):
        original[:, :, roi] = kernel[:, :, :, column].mean(axis=0)
        raw_original[:, :, roi] = raw_kernel[:, :, :, column].mean(axis=0)
        full_kernel[:, :, :, roi] = kernel[:, :, :, column]
        center[roi] = primary_center[column]
        centroid_full[roi] = centroid[column]
        center_distance[roi] = split_distance[column]
        center_quality[roi] = maps["center_fit_quality"][column]
    aligned_map, mask = shift_to_center(original, center)
    raw_aligned, _ = shift_to_center(raw_original, center)
    fly_mean, pixel_count = valid_mean(aligned_map, axis=2)
    raw_mean, _ = valid_mean(raw_aligned, axis=2)
    center_valid = np.isfinite(center).all(axis=1)
    unaligned_mean, _ = valid_mean(original[:, :, center_valid], axis=2)
    control_means = []
    for numerator in config.get("posthoc_diagnostic_shift_numerators_over_three", ()):
        shifted = np.roll(li_scaled, int(numerator) * (len(li_scaled) // 3), axis=0)
        control_kernel, control_maps = _stacked_kernels(design, shifted, bins)
        control_spatial = control_kernel.mean(axis=0)
        control_aligned, _ = shift_to_center(control_spatial, control_maps["centers"])
        control_means.append(valid_mean(control_aligned, axis=2)[0])
    controls = np.stack(control_means, axis=2) if control_means else np.empty((15, 15, 0))
    before = pairwise_median(original[:, :, center_valid])
    after = pairwise_median(aligned_map[:, :, center_valid])
    rows = []
    for roi, label in enumerate(aligned.roi_labels):
        reason = ("nonfinite_raw" if not finite[roi] else
                  "excess_zero_raw" if zero[roi] >= config["max_raw_zero_fraction"] else
                  "constant_raw" if raw_std[roi] <= config["minimum_response_std"] else
                  "constant_li_response" if roi not in selected else
                  "center_fit_unresolved" if not center_valid[roi] else "")
        rows.append({"fly_id": aligned.session.fly, "roi_id": label,
                     "full_payload_frames": len(raw), "rf_frames": int(np.sum(eligible)),
                     "raw_zero_fraction": float(zero[roi]), "raw_std": float(raw_std[roi]),
                     "included_center_aligned": bool(center_valid[roi]),
                     "exclusion_reason": reason,
                     "center_status": ("CENTER_UNCERTAIN" if center_valid[roi] and
                                       (not np.isfinite(center_distance[roi]) or center_distance[roi] >
                                        config["center_uncertain_split_distance_px"]) else
                                       "CENTER_ESTIMATED" if center_valid[roi] else "NO_CENTER"),
                     "gaussian_center_row": _finite(center[roi, 0]),
                     "gaussian_center_col": _finite(center[roi, 1]),
                     "energy_centroid_row": _finite(centroid_full[roi, 0]),
                     "energy_centroid_col": _finite(centroid_full[roi, 1]),
                     "split_center_distance_px": _finite(center_distance[roi]),
                     "gaussian_fit_quality": _finite(center_quality[roi]),
                     "source_results_sha256": aligned.qc["source_sha256"]["Results.csv"]})
    path = out / f"{aligned.session.fly}_rf.npz"
    np.savez_compressed(path, roi_labels=np.asarray(aligned.roi_labels),
                        full_kernel=full_kernel, original_spatial=original.astype(np.float32),
                        aligned_spatial=aligned_map.astype(np.float32), valid_pixel_mask=mask,
                        raw_original_spatial=raw_original.astype(np.float32),
                        raw_aligned_spatial=raw_aligned.astype(np.float32),
                        fly_mean=fly_mean.astype(np.float32), raw_fly_mean=raw_mean.astype(np.float32),
                        fly_unaligned_mean=unaligned_mean.astype(np.float32),
                        valid_pixel_count=pixel_count, gaussian_center=center,
                        energy_centroid=centroid_full, split_center_distance=center_distance,
                        posthoc_shift_control_fly_means=controls.astype(np.float32),
                        source_original_results_rows=aligned.original_sample_index[eligible])
    fly = {"fly_id": aligned.session.fly, "run_id": aligned.session.run_id,
           "total_roi": n_roi, "technical_valid_roi": int(len(selected)),
           "center_aligned_roi": int(np.sum(center_valid)),
           "center_uncertain_roi": sum(row["center_status"] == "CENTER_UNCERTAIN" for row in rows),
           "negative_signed_center_roi": int(np.sum(aligned_map[7, 7, center_valid] < 0)),
           "full_payload_frames": len(raw), "rf_frames": int(np.sum(eligible)),
           "li_reflection_margin_frames_each_edge": edge_margin,
           "median_split_center_distance_px": _finite(np.nanmedian(center_distance)),
           "within_fly_roi_pair_r_before": before, "within_fly_roi_pair_r_after": after,
           "source_hashes": aligned.qc["source_sha256"]}
    return fly, rows, fly_mean, raw_mean, unaligned_mean, controls, path


def _plot_maps(path: Path, maps: np.ndarray, labels: list[str], title: str,
               signed: bool = True) -> None:
    columns = 3
    rows = int(np.ceil(maps.shape[2] / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(11, 3.6 * rows), squeeze=False)
    bound = float(np.nanmax(np.abs(maps))) if signed else float(np.nanmax(maps))
    for i, axis in enumerate(axes.flat):
        if i >= maps.shape[2]:
            axis.axis("off")
            continue
        image = axis.imshow(maps[:, :, i], origin="lower", cmap="coolwarm" if signed else "viridis",
                            vmin=-bound if signed else 0, vmax=bound)
        axis.set_title(labels[i])
        axis.set_xlabel("grid column (px)")
        axis.set_ylabel("grid row (px)")
    fig.suptitle(title)
    fig.colorbar(image, ax=axes.ravel().tolist(), fraction=0.025, pad=0.03)
    fig.subplots_adjust(top=0.90, wspace=0.25, hspace=0.4, right=0.9)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_population(path: Path, mean: np.ndarray, spread: np.ndarray, count: np.ndarray) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7))
    bound = float(np.nanmax(np.abs(mean)))
    for axis, data, title, cmap, low, high in (
        (axes[0], mean, "Five-fly mean", "coolwarm", -bound, bound),
        (axes[1], spread, "Between-fly SD", "viridis", 0, float(np.nanmax(spread))),
        (axes[2], count, "Fly count per pixel", "viridis", 0, 5)):
        im = axis.imshow(data, origin="lower", cmap=cmap, vmin=low, vmax=high)
        axis.set_title(title)
        axis.set_xlabel("grid column (px)")
        axis.set_ylabel("grid row (px)")
        fig.colorbar(im, ax=axis, fraction=0.045)
    fig.suptitle("Descriptive population RF; n = 5 flies")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _plot_radial(path: Path, radius: np.ndarray, profiles: np.ndarray,
                 population: np.ndarray, spread: np.ndarray, individual: bool) -> None:
    fig, axis = plt.subplots(figsize=(7, 4))
    if individual:
        for i in range(profiles.shape[1]):
            axis.plot(radius, profiles[:, i], marker="o", label=f"fly{i+1}")
        axis.legend()
        title = "Five fly-level signed radial RF profiles"
    else:
        axis.plot(radius, population, marker="o", color="black", label="equal-fly mean")
        axis.fill_between(radius, population - spread, population + spread, alpha=.2,
                          color="gray", label="between-fly SD")
        axis.legend()
        title = "Population radial RF profile"
    axis.axhline(0, color="gray", linewidth=.8)
    axis.set(xlabel="radial distance (grid px)", ylabel="signed stimulus-response covariance",
             title=title)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def run_phase62(root: Path) -> Path:
    root = root.expanduser().resolve()
    config_path = root / "configs/phase6_2_population_rf.json"
    config = json.loads(config_path.read_text())
    if (config["schema_version"] != "phase6_2_population_rf_v1" or
        config["temporal_bins"] != 4 or config["updates_per_bin"] != 10 or
        config["center_fit_min_quality"] != 0.05 or
        not config["dog_require_opposite_center_surround_sign"] or
        not config["dog_require_all_lofo_polarities"]):
        raise ValueError("Unsupported frozen Phase 6.2 estimator")
    context = WorkflowContext.load(root)
    out = context.output_root / "phase_06" / "population_rf"
    out.mkdir(parents=True, exist_ok=True)
    sessions = discover_sessions(context.data_root)
    if len(sessions) != 5:
        raise ValueError("Phase 6.2 requires exactly five recorded flies")
    flies, roi_rows, maps, raw_maps, unaligned_maps, control_maps, paths = [], [], [], [], [], [], []
    input_paths = [config_path]
    for session in sessions:
        aligned = align_session(session)
        fly, rows, fly_map, raw_map, unaligned_map, controls, path = _one_fly(aligned, config, out)
        flies.append(fly)
        roi_rows.extend(rows)
        maps.append(fly_map)
        raw_maps.append(raw_map)
        unaligned_maps.append(unaligned_map)
        control_maps.append(controls)
        paths.append(path)
        input_paths.extend((session.path / "Results.csv",
                            session.path / "stimulus_package/stim_realized.npz",
                            session.path / "analysis_marker_lock/dlp_ttl_marker_locked.csv"))
    fly_maps = np.stack(maps, axis=2)
    raw_fly_maps = np.stack(raw_maps, axis=2)
    unaligned_fly_maps = np.stack(unaligned_maps, axis=2)
    controls_by_fly = np.stack(control_maps, axis=2)
    population, count = valid_mean(fly_maps, axis=2)
    raw_population, _ = valid_mean(raw_fly_maps, axis=2)
    unaligned_population, _ = valid_mean(unaligned_fly_maps, axis=2)
    control_population = np.stack([valid_mean(controls_by_fly[:, :, :, i], axis=2)[0]
                                   for i in range(controls_by_fly.shape[3])], axis=2)
    centered = np.where(np.isfinite(fly_maps), fly_maps - population[:, :, None], 0)
    spread = np.sqrt(np.divide(np.sum(centered ** 2, axis=2), count - 1,
                               out=np.full_like(population, np.nan), where=count > 1))
    leave_one_out = np.stack([valid_mean(np.delete(fly_maps, i, axis=2), axis=2)[0]
                              for i in range(len(flies))], axis=2)
    edges = np.asarray(config["radial_edges_pixels"], dtype=float)
    radius = (edges[:-1] + edges[1:]) / 2
    profiles = np.column_stack([radial_profile(fly_maps[:, :, i], edges)[0]
                                for i in range(len(flies))])
    population_profile, profile_count = valid_mean(profiles, axis=1)
    profile_spread = np.sqrt(np.divide(np.sum(np.where(np.isfinite(profiles),
                                profiles - population_profile[:, None], 0) ** 2, axis=1),
                                profile_count - 1, out=np.full(len(radius), np.nan),
                                where=profile_count > 1))
    gate = dog_gate(fly_maps, leave_one_out, config)
    dog = fit_radial_dog(radius, population_profile) if gate["descriptive_dog_gate"] else None
    population_path = out / "population_rf.npz"
    np.savez_compressed(population_path, fly_ids=np.asarray([row["fly_id"] for row in flies]),
                        fly_maps=fly_maps.astype(np.float32), population_mean=population.astype(np.float32),
                        between_fly_sd=spread.astype(np.float32), fly_count_per_pixel=count,
                        leave_one_fly_out=leave_one_out.astype(np.float32),
                        raw_fly_maps=raw_fly_maps.astype(np.float32),
                        raw_population_mean=raw_population.astype(np.float32),
                        unaligned_fly_maps=unaligned_fly_maps.astype(np.float32),
                        unaligned_population_mean=unaligned_population.astype(np.float32),
                        posthoc_shift_control_fly_maps=controls_by_fly.astype(np.float32),
                        posthoc_shift_control_population=control_population.astype(np.float32),
                        radial_edges_px=edges, radial_midpoints_px=radius,
                        fly_radial_profiles=profiles.astype(np.float32),
                        population_radial_profile=population_profile.astype(np.float32),
                        radial_between_fly_sd=profile_spread.astype(np.float32))
    roi_path = save_csv(out / "roi_inclusion_and_centers.csv", roi_rows)
    fly_path = save_csv(out / "fly_summary.csv", flies)
    labels = [row["fly_id"] for row in flies]
    figures = [out / f"figure_{number}.png" for number in range(1, 6)]
    _plot_maps(figures[0], fly_maps, labels, "Center-aligned signed mean RF by fly")
    _plot_population(figures[1], population, spread, count)
    _plot_radial(figures[2], radius, profiles, population_profile, profile_spread, False)
    _plot_radial(figures[3], radius, profiles, population_profile, profile_spread, True)
    lofo_labels = []
    for i, fly in enumerate(labels):
        correlation = image_correlation(population, leave_one_out[:, :, i])
        lofo_labels.append(f"without {fly}; r={correlation:.2f}" if correlation is not None
                           else f"without {fly}; r unavailable")
    _plot_maps(figures[4], leave_one_out, lofo_labels, "Leave-one-fly-out population RF")
    raw_figure = out / "supplement_raw_vs_li.png"
    _plot_maps(raw_figure, np.stack((population, raw_population), axis=2),
               ["Li-style primary", "raw diagnostic"], "Response sensitivity")
    alignment_figure = out / "supplement_unaligned_vs_aligned.png"
    _plot_maps(alignment_figure, np.stack((unaligned_population, population), axis=2),
               ["same ROIs, original coordinates", "same ROIs, centered"],
               "Effect of white-noise-derived center alignment")
    control_figure = out / "supplement_posthoc_shift_control.png"
    _plot_maps(control_figure, np.concatenate((population[:, :, None], control_population), axis=2),
               ["actual alignment", "response shifted by ~1/3 run", "response shifted by ~2/3 run"],
               "Post hoc temporal mismatch diagnostic; not a p-value")
    if dog is not None:
        figure = out / "figure_6_dog.png"
        fit = (dog["center_amplitude"] * np.exp(-.5 * (radius / dog["center_width_px"]) ** 2) +
               dog["surround_amplitude"] * np.exp(-.5 * (radius / dog["surround_width_px"]) ** 2) +
               dog["baseline"])
        fig, axis = plt.subplots(figsize=(7, 4))
        axis.plot(radius, population_profile, "o-", label="five-fly profile")
        axis.plot(radius, fit, "--", label="descriptive DoG fit")
        axis.axhline(0, color="gray", linewidth=.8)
        axis.set(xlabel="radial distance (grid px)", ylabel="signed covariance",
                 title="Conditional difference-of-Gaussians description")
        axis.legend()
        fig.tight_layout()
        fig.savefig(figure, dpi=180)
        plt.close(fig)
        figures.append(figure)
    lofo_correlation = {fly: image_correlation(population, leave_one_out[:, :, i])
                        for i, fly in enumerate(labels)}
    cross_fly_pairs = [image_correlation(fly_maps[:, :, i], fly_maps[:, :, j])
                       for i in range(5) for j in range(i + 1, 5)]
    original_pairs = [image_correlation(unaligned_fly_maps[:, :, i], unaligned_fly_maps[:, :, j])
                      for i in range(5) for j in range(i + 1, 5)]
    summary = {"status": "FULL-DATA DESCRIPTIVE ANALYSIS; not independent validation",
               "biological_replicates": 5, "stimulus_sequences": 1,
               "primary_response": config["primary_response"], "parameters": config,
               "total_roi": len(roi_rows),
               "center_aligned_roi": sum(row["included_center_aligned"] for row in roi_rows),
               "flies": flies, "leave_one_out_correlation_with_full": lofo_correlation,
               "median_cross_fly_map_r": _finite(np.median([r for r in cross_fly_pairs if r is not None])),
               "median_cross_fly_map_r_before_alignment": _finite(np.median(
                   [r for r in original_pairs if r is not None])),
               "center_surround": gate, "dog_fit": dog,
               "population_zone_means": zone_means(population, config["center_zone_radius_px"],
                                                    config["surround_zone_inner_px"],
                                                    config["surround_zone_outer_px"]),
               "raw_population_zone_means": zone_means(raw_population, config["center_zone_radius_px"],
                                                         config["surround_zone_inner_px"],
                                                         config["surround_zone_outer_px"]),
               "posthoc_shift_control_center_pixels": control_population[7, 7].tolist(),
               "posthoc_shift_control_zone_means": [zone_means(control_population[:, :, i],
                   config["center_zone_radius_px"], config["surround_zone_inner_px"],
                   config["surround_zone_outer_px"]) for i in range(control_population.shape[2])],
               "figure_files": [path.name for path in figures] +
                               [raw_figure.name, alignment_figure.name, control_figure.name]}
    summary_path = save_json(out / "summary.json", summary)
    return write_stage_manifest("phase_06_2_descriptive_population_rf", out, config,
        input_paths, [*paths, population_path, roi_path, fly_path, *figures, raw_figure,
                      alignment_figure, control_figure, summary_path], root,
        details={"five_fly_population": True, "center_aligned_roi": summary["center_aligned_roi"],
                 "dog_fitted": dog is not None})
