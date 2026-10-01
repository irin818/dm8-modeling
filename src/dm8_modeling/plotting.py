"""Seven graduation figures; RF units are normalized covariance, not membrane voltage."""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def finish(figure, path: Path, title: str) -> None:
    """Save one final PNG with a shared title and close its plotting resources."""
    figure.suptitle(title, fontsize=13)
    figure.tight_layout(rect=(0, 0, 1, .95))
    figure.savefig(path, dpi=180)
    plt.close(figure)


def final_figures(folder: Path, flies: list, population: dict, temporal: list,
                  models: list, projector: np.ndarray, null_values: np.ndarray,
                  null_summary: dict, config: dict) -> None:
    """Plot fixed spatial, temporal, model, null and support outputs from memory."""
    from .models import rotational_profile
    folder.mkdir(parents=True, exist_ok=True)
    names = [f"fly{i+1}" for i in range(len(flies))] + ["population"]
    images = [fly["map"] for fly in flies] + [population["map"]]
    limit = max(float(np.nanmax(np.abs(image))) for image in images)
    fig, axes = plt.subplots(2, 3, figsize=(11, 7), layout="constrained")
    for ax, image, name in zip(axes.ravel(), images, names, strict=True):
        shown = ax.imshow(image, cmap="RdBu_r", vmin=-limit, vmax=limit, origin="lower")
        ax.set(title=name, xlabel="Column (pixel)", ylabel="Row (pixel)")
    fig.colorbar(shown, ax=list(axes.ravel()), label="Normalized STRF covariance", shrink=.7)
    fig.suptitle("Figure 1 · Trimmed, subpixel-aligned RFs; population uses equal fly weights")
    fig.savefig(folder / "figure_1_rf_maps.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, zone in zip(axes, ("center", "surround"), strict=True):
        for name in names:
            rows = [row for row in temporal if row["fly"] == name]
            ax.plot([r["lag"] for r in rows], [r[zone] for r in rows],
                    label=name, lw=2.5 if name == "population" else 1,
                    alpha=1 if name == "population" else .55)
        ax.axhline(0, color="gray", lw=.7)
        ax.axvline(4, color="gray", ls=":", label="lag4 post-hoc candidate")
        ax.set(xlabel="Past update lag (nominal 1/15 s)", ylabel="Normalized STRF covariance", title=zone)
    axes[1].legend(fontsize=7)
    finish(fig, folder / "figure_2_temporal_rf.png",
           "Figure 2 · Full-record temporal diagnostic; fixed rounded reference centers")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    from .rf import zone_means
    zones = np.array([zone_means(image, config) for image in images])
    for index, (ax, zone) in enumerate(zip(axes, ("Center ≤1.5 px", "Surround 3–6 px"), strict=True)):
        ax.bar(names, zones[:, index], color=["#4878aa"]*len(flies)+["#d98442"])
        ax.axhline(0, color="gray", lw=.7)
        ax.set(title=zone, ylabel="Normalized STRF covariance")
    finish(fig, folder / "figure_3_fly_zones.png", "Figure 3 · Primary spatial center/surround by fly")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    shown = axes[0].imshow(population["map"], cmap="RdBu_r", origin="lower", vmin=-limit, vmax=limit)
    fig.colorbar(shown, ax=axes[0], label="Normalized STRF covariance")
    axes[0].set(xlabel="Column (pixel)", ylabel="Row (pixel)", title="Equal-fly population")
    profile = rotational_profile(population["map"], projector)
    axes[1].plot(np.arange(-7, 8), profile, "o", label="360° valid-support projection")
    for fit in models:
        if fit["unit"] == "population":
            axes[1].plot(fit["fit_positions_px"], fit["prediction"], label=fit["model"])
    axes[1].set(xlabel="Projected position (pixel)", ylabel="Projected covariance", title="Spatial fits (descriptive)")
    axes[1].legend(fontsize=8)
    finish(fig, folder / "figure_4_population_fit.png", "Figure 4 · Population RF and Gaussian/DoG fits")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for index, metric in enumerate(("r2", "aicc")):
        for model, offset, color in (("M1", -.18, "#4878aa"), ("M3", .18, "#d98442")):
            values = [next(f[metric] for f in models if f["unit"] == name and f["model"] == model) for name in names]
            axes[index].bar(np.arange(len(names))+offset, values, width=.36, label=model, color=color)
        axes[index].set_xticks(np.arange(len(names)), names)
        axes[index].set_ylabel("R² (higher is better)" if metric == "r2" else "AICc (lower is better)")
        axes[index].legend()
    axes[0].set_ylim(.85, 1.01)
    finish(fig, folder / "figure_5_model_comparison.png", "Figure 5 · M1 single Gaussian vs M3 antagonistic DoG")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for index, zone in enumerate(("center", "surround")):
        observed = null_summary[f"observed_{zone}"]
        p = null_summary["center_p_negative" if zone == "center" else "surround_p_positive"]
        axes[index].hist(null_values[:, index], bins=35, color="#4878aa", alpha=.8, label="Full-pipeline null")
        axes[index].axvline(observed, color="#b33e43", lw=2, label=f"Observed {observed:.6f}")
        axes[index].set(title=f"{zone}: one-sided p={p:.6f}", xlabel="Normalized zone covariance", ylabel="Iterations")
        axes[index].legend(fontsize=8)
    finish(fig, folder / "figure_6_full_pipeline_null.png",
           f"Figure 6 · {len(null_values)} raw circular shifts, reselect lag and recenter each iteration")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, key, label in zip(axes, ("roi_support", "fly_support"), ("ROI contributors", "Fly contributors"), strict=True):
        shown = ax.imshow(population[key], origin="lower", cmap="viridis")
        fig.colorbar(shown, ax=ax, label=label)
        ax.set(title=label, xlabel="Column (pixel)", ylabel="Row (pixel)")
    finish(fig, folder / "figure_7_coverage.png", "Figure 7 · Finite support after subpixel translation; missing ≠ zero")
