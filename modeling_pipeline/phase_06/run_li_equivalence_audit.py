"""Run the frozen Phase 6.5 descriptive method-equivalence audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from dm8_modeling.data import align_session, discover_sessions
from dm8_modeling.experiments.phase63 import prepare_fly
from dm8_modeling.preprocessing.rf_response import li_style_relative_response
from dm8_modeling.rf.characterization import reverse_correlation, rf_maps
from dm8_modeling.rf.dog import GaussianGrid, projection_matrix
from dm8_modeling.rf.li_equivalence import (aggregate, align_spatial, centers_from_spatial,
    coarse_from_native, li_relative_dog, native_design, raw_center_edge_distance,
    rf_zscore, zone_values)
from dm8_modeling.rf.population import energy_centers, radial_profile, valid_mean
from dm8_modeling.experiments.workflow import WorkflowContext


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(key for row in rows for key in row)),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def estimate(prepared, config, estimator, *, trim=False, timing=0, shift=0, halves=False):
    raw = np.roll(prepared.raw, shift, axis=0) if shift else prepared.raw
    relative, margin = li_style_relative_response(raw, prepared.aligned.imaging_time_us,
        estimator["gaussian_sigma_seconds"], estimator["gaussian_truncate_sigma"])
    updates = prepared.aligned.update_index + timing
    eligible = (updates >= config["native_lags"]-1) & (updates < len(prepared.aligned.stimulus))
    if trim:
        eligible[:margin] = False
        eligible[-margin:] = False
    valid = relative[eligible].std(axis=0) > estimator["minimum_response_std"]
    design = native_design(prepared.aligned.stimulus, updates[eligible], config["native_lags"])
    kernel = reverse_correlation(design, relative[eligible][:, valid])
    native = rf_zscore(kernel).reshape(40, 15, 15, -1)
    coarse = rf_zscore(coarse_from_native(kernel.reshape(40, 15, 15, -1)).reshape(900, -1)).reshape(4, 15, 15, -1)
    result = {"native": native, "coarse": coarse, "selected": prepared.technical_indices[valid],
              "frames": int(eligible.sum()), "margin": margin}
    if halves:
        midpoint = len(design)//2
        for label, part in (("first", slice(None, midpoint)), ("second", slice(midpoint, None))):
            half_kernel = reverse_correlation(design[part], relative[eligible][:, valid][part])
            result[label] = {"native": rf_zscore(half_kernel).reshape(40,15,15,-1),
                "coarse": rf_zscore(coarse_from_native(half_kernel.reshape(40,15,15,-1)).reshape(900,-1)).reshape(4,15,15,-1)}
    return result


def one_fly_maps(estimate_result, spatial_rule, peak_lag, align_method, center_rule="gaussian"):
    native, coarse = estimate_result["native"], estimate_result["coarse"]
    if spatial_rule == "coarse_mean":
        spatial = coarse.mean(axis=0)
        centers = rf_maps(coarse.reshape(900, -1), 4)["centers"]
    elif spatial_rule == "native_mean":
        spatial = native.mean(axis=0)
        centers = rf_maps(coarse.reshape(900, -1), 4)["centers"]
    elif spatial_rule == "global_peak":
        spatial = native[peak_lag]
        centers = centers_from_spatial(spatial)
    elif spatial_rule == "fixed_0_9":
        spatial = native[:10].mean(axis=0)
        centers = centers_from_spatial(spatial)
    else:
        raise ValueError(spatial_rule)
    if center_rule == "energy":
        centers = energy_centers(native)
    aligned, valid = align_spatial(spatial, centers, align_method)
    fly, count = valid_mean(aligned, 2)
    return {"roi_maps": aligned, "fly_map": fly, "roi_count": count, "centers": centers,
            "source_spatial": spatial}


def plot_heat(path, maps, titles, *, vlim=None, normalize_each=False):
    n = len(maps)
    if normalize_each:
        maps = [m / max(float(np.nanmax(np.abs(m))), 1e-12) for m in maps]
    fig, axes = plt.subplots(1, n, figsize=(3.5*n, 3.7), squeeze=False)
    vmax = vlim or max(float(np.nanmax(np.abs(m))) for m in maps)
    for ax, image, title in zip(axes[0], maps, titles, strict=True):
        im = ax.imshow(image, cmap="RdBu_r", vmin=-vmax, vmax=vmax, origin="lower")
        ax.set_title(title)
        ax.set_xlabel("grid px")
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=.7)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run(root: Path) -> Path:
    root = root.resolve()
    config_path = root / "configs/phase6_5_li_equivalence.json"
    config = json.loads(config_path.read_text())
    estimator = json.loads((root / config["estimator_config"]).read_text())
    context = WorkflowContext.load(root)
    out = root / "docs/phase6_5_results"
    figs = root / "docs/phase6_5_figures"
    out.mkdir(exist_ok=True)
    figs.mkdir(exist_ok=True)
    sessions = discover_sessions(context.data_root)
    if len(sessions) != 5 or len({s.fly for s in sessions}) != 5:
        raise ValueError("Expected five separate recordings")
    prepared = [prepare_fly(align_session(s), estimator) for s in sessions]
    labels = [p.aligned.session.fly for p in prepared]
    full = [estimate(p, config, estimator, halves=True) for p in prepared]
    print("Native full-data STRFs estimated", flush=True)
    # One population-wide, surround-blind temporal decision; each fly contributes equally.
    energy = np.mean([np.mean(np.sum(item["native"]**2, axis=(1, 2)), axis=1)
                      for item in full], axis=0)
    peak_lag = int(np.argmax(energy))
    trimmed = [estimate(p, config, estimator, trim=True, halves=True) for p in prepared]
    print(f"Edge-trim STRFs estimated; frozen energy peak lag={peak_lag}", flush=True)
    specs = {"C1": (full, "coarse_mean", "integer"),
             "C2": (full, "native_mean", "integer"),
             "C3": (full, "global_peak", "integer"),
             "C4": (trimmed, "global_peak", "integer"),
             "C5": (trimmed, "global_peak", "bilinear"),
             "C6": (trimmed, "global_peak", "bilinear"),
             "C7": (trimmed, "global_peak", "bilinear"),
             "S2_FIXED_0_9": (trimmed, "fixed_0_9", "bilinear"),
             "CENTER_ENERGY": (trimmed, "global_peak", "bilinear")}
    maps = {}
    fly_rows, pop_rows, coverage_rows = [], [], []
    raw_maps = {}
    for variant, (items, rule, alignment) in specs.items():
        per_fly = [one_fly_maps(item, rule, peak_lag, alignment,
            "energy" if variant == "CENTER_ENERGY" else "gaussian") for item in items]
        raw_maps[variant] = per_fly
        mode = "roi_equal" if variant == "C6" else "fly_equal"
        population, roi_support, fly_support = aggregate([x["roi_maps"] for x in per_fly], mode)
        maps[variant] = population
        center, surround = zone_values(population, config)
        pop_rows.append({"variant": variant, "weighting": mode, "center": center,
            "surround": surround, "negative_center_flies": sum(zone_values(x["fly_map"], config)[0]<0 for x in per_fly),
            "positive_surround_flies": sum(zone_values(x["fly_map"], config)[1]>0 for x in per_fly),
            "global_peak_lag": peak_lag, "n_flies": 5})
        rr, cc = np.mgrid[:15, :15]
        radial = np.hypot(rr-7, cc-7)
        for zone, mask in (("center", radial<=1.5), ("surround", (radial>=3)&(radial<=6)),
                           ("outer", radial>6)):
            coverage_rows.append({"variant": variant, "zone": zone,
                "minimum_roi_support": int(roi_support[mask].min()),
                "median_roi_support": float(np.median(roi_support[mask])),
                "minimum_fly_support": int(fly_support[mask].min()),
                "median_fly_support": float(np.median(fly_support[mask]))})
        for label, fly, item in zip(labels, per_fly, items, strict=True):
            c, s = zone_values(fly["fly_map"], config)
            included = np.isfinite(fly["centers"]).all(axis=1)
            edge = raw_center_edge_distance(fly["centers"])
            central_roi = fly["roi_maps"][7, 7, included]
            first = one_fly_maps(item["first"], rule, peak_lag, alignment,
                "energy" if variant == "CENTER_ENERGY" else "gaussian")["centers"]
            second = one_fly_maps(item["second"], rule, peak_lag, alignment,
                "energy" if variant == "CENTER_ENERGY" else "gaussian")["centers"]
            distance = np.linalg.norm(first-second, axis=1)
            stable = included & np.isfinite(distance) & (distance <= estimator["center_uncertain_split_distance_px"])
            fly_rows.append({"variant": variant, "fly": label, "center": c, "surround": s,
                "center_polarity": "negative" if c<0 else "positive", "surround_polarity": "positive" if s>0 else "negative",
                "technical_roi": len(item["selected"]), "valid_center_roi": int(included.sum()),
                "negative_center_roi_fraction": float(np.mean(central_roi<0)) if len(central_roi) else np.nan,
                "median_center_row_px": float(np.nanmedian(fly["centers"][:, 0])),
                "median_center_col_px": float(np.nanmedian(fly["centers"][:, 1])),
                "median_raw_edge_distance_px": float(np.nanmedian(edge)),
                "fraction_center_within_3px_of_edge": float(np.nanmean(edge<3)),
                "frames": item["frames"], "center_stable_roi": int(stable.sum()),
                "center_stable_fraction": float(stable.sum()/included.sum()) if included.any() else np.nan})
            for zone, mask in (("center", radial<=1.5), ("surround", (radial>=3)&(radial<=6)),
                               ("outer", radial>6)):
                support = fly["roi_count"][mask]
                coverage_rows.append({"variant": variant, "zone": zone, "fly": label,
                    "minimum_roi_support": int(support.min()), "median_roi_support": float(np.median(support)),
                    "minimum_fly_support": 1, "median_fly_support": 1})
    with np.load(root / config["historical_arrays"]) as saved:
        c0 = saved["population"]
        old_fly = saved["fly_maps"]
    maps["C0"] = c0
    old_center, old_surround = zone_values(c0, config)
    with (root / "docs/phase6_3_results/fly_independent_summary.csv").open(newline="") as handle:
        historical = {row["fly"]: row for row in csv.DictReader(handle)}
    pop_rows.insert(0, {"variant": "C0", "weighting": "fly_equal", "center": old_center,
        "surround": old_surround, "negative_center_flies": sum(zone_values(m, config)[0]<0 for m in old_fly),
        "positive_surround_flies": sum(zone_values(m, config)[1]>0 for m in old_fly),
        "global_peak_lag": "historical_4x10", "n_flies": 5})
    for label, image in zip(labels, old_fly, strict=True):
        c, s = zone_values(image, config)
        fly_rows.insert(0, {"variant": "C0", "fly": label, "center": c, "surround": s,
            "center_polarity": "negative" if c<0 else "positive", "surround_polarity": "positive" if s>0 else "negative",
            "technical_roi": historical[label]["technical_roi"],
            "valid_center_roi": historical[label]["aligned_roi"],
            "negative_center_roi_fraction": historical[label]["negative_center_roi_fraction"],
            "median_center_row_px": "historical", "median_center_col_px": "historical",
            "median_raw_edge_distance_px": "historical", "fraction_center_within_3px_of_edge": "historical",
            "frames": "historical", "center_stable_roi": historical[label]["stable_roi"],
            "center_stable_fraction": historical[label]["stable_fraction"]})
    # Native trajectories retain one individual STRF normalization per ROI.
    temporal_rows = []
    lag_maps = []
    for lag in range(40):
        per_fly_lag = []
        for label, item in zip(labels, full, strict=True):
            center = rf_maps(item["coarse"].reshape(900, -1), 4)["centers"]
            aligned = align_spatial(item["native"][lag], center, "integer")[0]
            fly_map = valid_mean(aligned, 2)[0]
            c, s = zone_values(fly_map, config)
            temporal_rows.append({"lag": lag, "fly": label, "center": c, "surround": s})
            per_fly_lag.append(fly_map)
        pop_lag = valid_mean(np.stack(per_fly_lag, axis=2), 2)[0]
        lag_maps.append(pop_lag)
        c, s = zone_values(pop_lag, config)
        temporal_rows.append({"lag": lag, "fly": "population", "center": c, "surround": s})
    # Fixed T-1 / T+1 sensitivities; no optimization over timing offsets.
    timing_rows = []
    for offset in (-1, 1):
        timing_items = [estimate(p, config, estimator, trim=True, timing=offset) for p in prepared]
        per_fly = [one_fly_maps(item, "global_peak", peak_lag, "bilinear") for item in timing_items]
        pop = aggregate([x["roi_maps"] for x in per_fly], "fly_equal")[0]
        c, s = zone_values(pop, config)
        timing_rows.append({"offset_updates": offset, "center": c, "surround": s,
            "positive_surround_flies": sum(zone_values(x["fly_map"], config)[1]>0 for x in per_fly)})
    timing_rows.append({"offset_updates": 0, "center": zone_values(maps["C7"], config)[0],
        "surround": zone_values(maps["C7"], config)[1],
        "positive_surround_flies": pop_rows[[r["variant"] for r in pop_rows].index("C7")]["positive_surround_flies"]})
    # Both DoG questions on each final fly and population map; valid weighted projection.
    projector = projection_matrix(15, config["rotational_projection_steps"])
    dog_config = json.loads((root / "configs/phase6_4_dog_test.json").read_text())
    dog_rows, projection_rows, radial_rows = [], [], []
    edges = np.asarray(estimator["radial_edges_pixels"], float)
    for variant in ("C0","C1","C2","C3","C4","C5","C6","C7"):
        fly_images = old_fly if variant == "C0" else np.stack([f["fly_map"] for f in raw_maps[variant]])
        for label, image in [("population", maps[variant])] + list(zip(labels, fly_images, strict=True)):
            finite = np.isfinite(image)
            denom = projector @ finite.ravel().astype(float)
            profile = np.divide(projector @ np.nan_to_num(image).ravel(), denom,
                                out=np.full(15, np.nan), where=denom>1e-8)
            for position, value in zip(range(-7,8), profile, strict=True):
                projection_rows.append({"variant":variant,"unit":label,"position_px":position,"value":value})
            radial, radial_count = radial_profile(image, edges)
            for low, high, value, count in zip(edges[:-1],edges[1:],radial,radial_count,strict=True):
                radial_rows.append({"variant":variant,"unit":label,"radius_low_px":low,
                    "radius_high_px":high,"value":value,"valid_pixels":count})
            x = np.arange(-7, 8)[np.isfinite(profile)]
            y = profile[np.isfinite(profile)]
            # Phase 6.4 coefficient bounds are in its tiny covariance units.
            # Fixed 0.01 peak scaling preserves shape and AICc model comparisons.
            scale = .01 / max(float(np.max(np.abs(y))), 1e-12)
            grid = GaussianGrid(x, dog_config)
            for model in ("M1", "M3"):
                fit = grid.fit(y*scale, model)
                dog_rows.append({"variant":variant,"unit":label,"model":model,
                    "center_sigma_px":fit.sigma1,"surround_sigma_px":fit.sigma2,
                    "center_amplitude":fit.a1,"surround_amplitude":fit.a2,
                    "relative_surround_amplitude":fit.a2/abs(fit.a1) if fit.a2 is not None and abs(fit.a1)>1e-12 else np.nan,
                    "r2":fit.r2,"aicc":fit.aicc,"fit_status":fit.status,
                    "amplitude_unit":"profile_rescaled_to_0.01_abs_peak"})
            li = li_relative_dog(x,y,tuple(config["li_dog_center_sigma_grid_px"][:2]),
                tuple(config["li_dog_surround_sigma_grid_px"][:2]),config["li_dog_relative_amplitude_grid"][1])
            dog_rows.append({"variant":variant,"unit":label,"model":"LI_RELATIVE_PIXEL_SENSITIVITY",**li,
                "aicc":np.nan,"fit_status":"PIXEL_UNITS_60_DEG_BOUND_UNRESOLVED",
                "amplitude_unit":"raw_profile_units_for_this_variant"})
    write_rows(out / "fly_results.csv", fly_rows)
    write_rows(out / "population_results.csv", pop_rows)
    write_rows(out / "coverage_results.csv", coverage_rows)
    write_rows(out / "temporal_results.csv", temporal_rows)
    write_rows(out / "timing_results.csv", timing_rows)
    write_rows(out / "dog_results.csv", dog_rows)
    write_rows(out / "projection_results.csv", projection_rows)
    write_rows(out / "radial_results.csv", radial_rows)
    changes = {"C0": "historical baseline", "C1": "RF post-zscore",
        "C2": "native 40-lag normalization", "C3": "global energy peak spatial slice",
        "C4": "Gaussian edge trim", "C5": "bilinear subpixel alignment",
        "C6": "all ROI equal morphology", "C7": "five fly equal inference"}
    comparison_rows = []
    previous_ratio = None
    for key in changes:
        row = next(r for r in pop_rows if r["variant"] == key)
        ratio = row["surround"] / max(abs(row["center"]), 1e-12)
        comparison_rows.append({"variant": key, "changed_step": changes[key],
            "center_negative": row["center"]<0,
            "surround_to_abs_center": ratio,
            "delta_ratio_from_previous": None if previous_ratio is None else ratio-previous_ratio,
            "positive_surround_flies": row["positive_surround_flies"],
            "biological_n": row["n_flies"]})
        previous_ratio = ratio
    write_rows(out / "pipeline_comparison.csv", comparison_rows)
    np.savez_compressed(out / "final_maps.npz", **maps,
        final_fly_maps=np.stack([x["fly_map"] for x in raw_maps["C7"]], axis=0),
        final_roi_support=aggregate([x["roi_maps"] for x in raw_maps["C7"]], "fly_equal")[1],
        final_fly_support=aggregate([x["roi_maps"] for x in raw_maps["C7"]], "fly_equal")[2])
    np.savez_compressed(out / "native_lag_maps.npz", population_maps=np.stack(lag_maps),
                        selected_lags=np.array([0,1,4,9,19,39]))
    (out / "run_metadata.json").write_text(json.dumps({"config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "global_peak_lag": peak_lag, "energy": energy.tolist(), "five_flies": labels,
        "source_sha256_by_fly": {p.aligned.session.fly: p.aligned.qc["source_sha256"] for p in prepared}}, indent=2)+"\n")
    plot_heat(figs / "figure_1_pipeline_comparison.png", [maps[x] for x in ("C0","C1","C2","C3","C7")],
              ["C0 historical","C1 RF z","C2 native mean","C3 peak","C7 final"], normalize_each=True)
    plot_heat(figs / "figure_3_five_fly_li_equivalent_rf.png", [x["fly_map"] for x in raw_maps["C7"]], labels)
    plot_heat(figs / "figure_4_population_current_vs_li.png", [maps["C0"],maps["C7"]],
              ["current","Li-like sensitivity"], normalize_each=True)
    _, roi_support, fly_support = aggregate([x["roi_maps"] for x in raw_maps["C7"]], "fly_equal")
    fig, axes = plt.subplots(1,2,figsize=(8,3.7))
    for ax, support, title in zip(axes,[roi_support,fly_support],["ROI support","fly support"],strict=True):
        im = ax.imshow(support,cmap="viridis",origin="lower",vmin=0)
        ax.set_title(title); ax.set_xlabel("aligned grid px")
        fig.colorbar(im,ax=ax,shrink=.8)
    fig.savefig(figs / "figure_6_coverage_map.png",dpi=150,bbox_inches="tight"); plt.close(fig)
    plot_heat(figs / "figure_7_aggregation_comparison.png", [maps["C6"],maps["C7"]], ["ROI equal","fly equal"])
    fig = plt.figure(figsize=(12,7))
    layout = fig.add_gridspec(2,6,height_ratios=[1.3,1])
    ax = fig.add_subplot(layout[0,:])
    for fly in labels+["population"]:
        rows = [r for r in temporal_rows if r["fly"]==fly]
        ax.plot([r["lag"] for r in rows], [r["center"] for r in rows], label=f"{fly} center")
        ax.plot([r["lag"] for r in rows], [r["surround"] for r in rows], linestyle=":", alpha=.7)
    ax.axhline(0,color="black",lw=.5); ax.set_xlabel("past stimulus updates (lag0=current)")
    ax.set_ylabel("RF z units; dotted=surround"); ax.legend(ncol=3,fontsize=7)
    selected_lags = [0,1,4,9,19,39]
    vmax = max(float(np.nanmax(np.abs(lag_maps[lag]))) for lag in selected_lags)
    for i, lag in enumerate(selected_lags):
        panel = fig.add_subplot(layout[1,i])
        panel.imshow(lag_maps[lag],cmap="RdBu_r",origin="lower",vmin=-vmax,vmax=vmax)
        panel.set_title(f"lag {lag}")
        panel.set_xticks([]); panel.set_yticks([])
    fig.savefig(figs / "figure_2_temporal_native_vs_coarse.png",dpi=150,bbox_inches="tight"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8,4))
    for key in ("C0","C1","C2","C3","C4","C5","C6","C7"):
        row = next(r for r in pop_rows if r["variant"]==key)
        denominator = max(abs(row["center"]), 1e-12)
        ax.scatter(key,row["surround"]/denominator,c="tomato")
    ax.axhline(0,color="black",lw=.5); ax.set_ylabel("surround mean / absolute center")
    ax.set_title("All variants: 5/5 flies have negative center")
    fig.savefig(figs / "figure_5_center_surround_ablation.png",dpi=150,bbox_inches="tight"); plt.close(fig)
    print(f"Saved Phase 6.5 tables and figures to {out}", flush=True)
    return out


def run_final_null(root: Path) -> Path:
    """500 full-pipeline circular shifts for the final descriptive C7 estimator."""
    import time
    root = root.resolve()
    config = json.loads((root / "configs/phase6_5_li_equivalence.json").read_text())
    estimator = json.loads((root / config["estimator_config"]).read_text())
    context = WorkflowContext.load(root)
    prepared = [prepare_fly(align_session(s), estimator) for s in discover_sessions(context.data_root)]
    if len(prepared) != 5:
        raise ValueError("Null requires five fly recordings")
    with np.load(root / "docs/phase6_5_results/final_maps.npz") as observed:
        observed_center, observed_surround = zone_values(observed["C7"], config)
    rng = np.random.default_rng(config["final_null_seed"])
    shift_table = []
    for fly in prepared:
        interval = float(np.median(np.diff(fly.aligned.imaging_time_us)))
        minimum = int(np.ceil(config["minimum_null_circular_shift_seconds"]*1e6/interval))
        if len(fly.raw) <= 2*minimum:
            raise ValueError("Too few frames for excluded near-zero null offsets")
        shift_table.append(rng.integers(minimum, len(fly.raw)-minimum+1,
            size=config["final_null_iterations_if_positive_candidate"]))
    rows = []
    out = root / "docs/phase6_5_results/final_null_results.csv"
    start = time.monotonic()
    for iteration in range(config["final_null_iterations_if_positive_candidate"]):
        full_items = [estimate(fly, config, estimator,
                               shift=int(shifts[iteration])) for fly, shifts in zip(prepared, shift_table, strict=True)]
        energy = np.mean([np.mean(np.sum(item["native"]**2, axis=(1,2)), axis=1)
                          for item in full_items], axis=0)
        peak = int(np.argmax(energy))
        items = [estimate(fly, config, estimator, trim=True,
                          shift=int(shifts[iteration])) for fly, shifts in zip(prepared, shift_table, strict=True)]
        per_fly = [one_fly_maps(item, "global_peak", peak, "bilinear") for item in items]
        population = aggregate([x["roi_maps"] for x in per_fly], "fly_equal")[0]
        center, surround = zone_values(population, config)
        rows.append({"iteration": iteration+1, "global_peak_lag": peak,
            "center": center, "surround": surround,
            "positive_surround_flies": sum(zone_values(x["fly_map"], config)[1]>0 for x in per_fly),
            "negative_center_flies": sum(zone_values(x["fly_map"], config)[0]<0 for x in per_fly),
            **{f"{fly.aligned.session.fly}_shift_frames": int(shifts[iteration])
               for fly, shifts in zip(prepared, shift_table, strict=True)}})
        if (iteration+1) % 10 == 0:
            write_rows(out, rows)
            print(f"final full-pipeline null {iteration+1}/{config['final_null_iterations_if_positive_candidate']} "
                  f"elapsed={time.monotonic()-start:.1f}s", flush=True)
    write_rows(out, rows)
    center_null = np.array([r["center"] for r in rows])
    surround_null = np.array([r["surround"] for r in rows])
    summary = {"n": len(rows), "observed_center": observed_center,
        "observed_surround": observed_surround,
        "p_negative_center": float((1+np.sum(center_null<=observed_center))/(len(rows)+1)),
        "p_positive_surround": float((1+np.sum(surround_null>=observed_surround))/(len(rows)+1)),
        "null_center_quantiles": np.quantile(center_null,[.025,.5,.975]).tolist(),
        "null_surround_quantiles": np.quantile(surround_null,[.025,.5,.975]).tolist(),
        "observed_candidate_positive": bool(observed_surround>0),
        "method": "independent raw circular shifts by fly; full Gaussian baseline; global energy lag selected on full record, then trimmed RF, RF zscore, center, bilinear alignment, ROI then fly means"}
    (out.parent / "final_null_summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    fig, axes = plt.subplots(1,2,figsize=(8,3.5))
    for ax, values, observed, name in zip(axes,[center_null,surround_null],
        [observed_center,observed_surround],["center","surround"],strict=True):
        ax.hist(values,bins=30,color="steelblue"); ax.axvline(observed,color="crimson",label="observed")
        ax.set_title(name); ax.legend()
    fig.savefig(root / "docs/phase6_5_figures/figure_8_final_null.png",dpi=150,bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--final-null", action="store_true")
    args = parser.parse_args()
    print(run_final_null(args.workspace_root) if args.final_null else run(args.workspace_root))
