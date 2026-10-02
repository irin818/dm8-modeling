"""A4-width thesis figures from unchanged RF arrays; PNG 300 dpi and editable SVG."""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np
from .rf import zone_means

WIDTH = 6.7  # 170 mm, within A4 text width.
FLY_COLORS = ["#315b78", "#577e98", "#7094ae", "#426e8c", "#8eacbf"]
FLY_MARKERS = ["o", "s", "^", "v", "P"]
FLY_STYLES = ["-", "--", "-.", ":", (0, (4, 1, 1, 1))]
RF_CMAP = LinearSegmentedColormap.from_list("signed_covariance", ["#245579", "white", "#bd5537"])
STYLE = {"font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 9,
         "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8,
         "legend.fontsize": 7.5, "axes.linewidth": .7, "svg.fonttype": "none",
         "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white"}


def save_figure(figure, folder: Path, stem: str) -> None:
    """Export one figure as 300 dpi PNG and SVG; no data changes or date stamp."""
    figure.savefig(folder/f"{stem}.png", dpi=300)
    figure.savefig(folder/f"{stem}.svg", metadata={"Date": None})
    plt.close(figure)


def panel_axis(axis, label: str, title: str) -> None:
    """Apply shared line/scatter axes and an external bold panel label."""
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(length=3, width=.7)
    axis.set_title(title, pad=9)
    axis.text(-.16, 1.06, label, transform=axis.transAxes, fontsize=11, fontweight="bold")


def receptive_field_figure(folder: Path, flies: list, population: dict) -> None:
    """Six square [15,15] RFs share one linear symmetric zero-centered color scale."""
    images = [fly["map"] for fly in flies] + [population["map"]]
    limit = max(float(np.nanmax(np.abs(image))) for image in images)
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    fig, axes = plt.subplots(2, 3, figsize=(WIDTH, 4.7), layout="constrained", sharex=True, sharey=True)
    for index, (axis, image) in enumerate(zip(axes.ravel(), images, strict=True)):
        name = f"Fly {index+1}" if index < len(flies) else "Population"
        shown = axis.imshow(image, cmap=RF_CMAP, norm=norm, origin="lower", interpolation="nearest")
        axis.set_box_aspect(1)
        axis.set_title(name, fontweight="bold" if index == len(flies) else "normal", pad=7)
        axis.text(-.12, 1.04, chr(65+index), transform=axis.transAxes, fontsize=11, fontweight="bold")
        axis.plot(7, 7, marker="+", color="black", markersize=6, markeredgewidth=.8)
        axis.set_xticks([0, 7, 14])
        axis.set_yticks([0, 7, 14])
        axis.tick_params(length=2)
        if index//3 == 1:
            axis.set_xlabel("Column (pixel)")
        if index%3 == 0:
            axis.set_ylabel("Row (pixel)")
        for spine in axis.spines.values():
            spine.set_color("black" if index == len(flies) else "#aaaaaa")
            spine.set_linewidth(1.2 if index == len(flies) else .5)
    colorbar = fig.colorbar(shown, ax=list(axes.ravel()), orientation="horizontal", fraction=.05, pad=.06, aspect=35)
    colorbar.set_label("Normalized STRF covariance")
    colorbar.set_ticks([-limit, 0, limit])
    colorbar.ax.xaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    save_figure(fig, folder, "figure_1_receptive_fields")


def spatial_zone_figure(folder: Path, flies: list, population: dict, config: dict) -> None:
    """All five fly zone values and the equal-fly population use separate y scales, no SEM."""
    zones = np.array([zone_means(fly["map"], config) for fly in flies] + [zone_means(population["map"], config)])
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 2.9))
    fig.subplots_adjust(left=.11, right=.98, bottom=.23, top=.83, wspace=.43)
    for column, axis in enumerate(axes):
        panel_axis(axis, chr(65+column), "Center (≤1.5 pixel)" if column == 0 else "Surround (3–6 pixel)")
        for fly in range(len(flies)):
            axis.scatter(fly, zones[fly, column], s=35, marker=FLY_MARKERS[fly],
                         color=FLY_COLORS[fly], edgecolors="black", linewidths=.5, zorder=3)
        axis.scatter(len(flies), zones[-1, column], s=65, marker="D", facecolor="white", edgecolors="black", linewidths=1.4, zorder=4)
        axis.axhline(0, color="#777777", lw=.7)
        axis.set_xticks(range(len(flies)+1), [f"fly{i+1}" for i in range(len(flies))]+["Pop."])
        axis.set(xlabel="Fly (biological n = 5)", ylabel="Normalized STRF covariance", xlim=(-.5, len(flies)+.5))
        low, high = min(0, zones[:, column].min()), max(0, zones[:, column].max())
        margin = max((high-low)*.12, 1e-6)
        axis.set_ylim(low-margin, high+margin)
        axis.yaxis.set_major_locator(MaxNLocator(5))
        axis.yaxis.set_major_formatter(FormatStrFormatter("%.1f" if column == 0 else "%.3f"))
    save_figure(fig, folder, "figure_2_spatial_zones")


def temporal_figure(folder: Path, temporal: list) -> None:
    """Plot all 40 frozen full-record diagnostic lags; no smoothing or significance marks."""
    names = [f"fly{i+1}" for i in range(5)] + ["population"]
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 3.3))
    fig.subplots_adjust(left=.11, right=.98, bottom=.19, top=.80, wspace=.42)
    handles = []
    for column, (axis, zone) in enumerate(zip(axes, ("center", "surround"), strict=True)):
        panel_axis(axis, chr(65+column), "Center trajectory" if column == 0 else "Surround trajectory")
        for index, name in enumerate(names):
            rows = sorted((row for row in temporal if row["fly"] == name), key=lambda row: row["lag"])
            line, = axis.plot([row["lag"] for row in rows], [row[zone] for row in rows],
                color=FLY_COLORS[index] if index < 5 else "#222222",
                linestyle=FLY_STYLES[index] if index < 5 else "-",
                linewidth=.9 if index < 5 else 2.2, alpha=.60 if index < 5 else 1,
                label=name if index < 5 else "Population", zorder=2 if index < 5 else 4)
            if column == 0:
                handles.append(line)
        axis.axhline(0, color="#777777", lw=.7)
        axis.set(xlim=(0,39), xlabel="Stimulus update lag", ylabel="Normalized STRF covariance")
        axis.set_xticks([0,10,20,30,39])
        lag = 1 if column == 0 else 4
        point = next(row[zone] for row in temporal if row["fly"] == "population" and row["lag"] == lag)
        axis.axvline(lag, color="#999999", lw=.7, ls="--" if column == 0 else ":", zorder=1)
        axis.annotate("lag1: primary\nearly center" if column == 0 else "lag4: post-hoc\nperipheral candidate",
            xy=(lag, point), xytext=(.36,.14) if column == 0 else (.37,.86),
            textcoords="axes fraction", fontsize=7.5, va="bottom", arrowprops={"arrowstyle":"-", "color":"#555555", "lw":.6})
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.52,1), ncol=6, frameon=False, handlelength=2.2, columnspacing=.9)
    save_figure(fig, folder, "figure_3_temporal_rf")


def null_figure(folder: Path, values: np.ndarray, summary: dict) -> None:
    """Show all 500 null samples, observed statistics and quantiles; inset is labeled."""
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 3.4))
    fig.subplots_adjust(left=.09, right=.98, bottom=.25, top=.84, wspace=.31)
    for column, (axis, zone) in enumerate(zip(axes, ("center", "surround"), strict=True)):
        panel_axis(axis, chr(65+column), "Center null" if column == 0 else "Surround null")
        axis.hist(values[:, column], bins=30, color="#a9c1d3", edgecolor="white", linewidth=.25)
        for index, quantile in enumerate(summary[f"{zone}_null_quantiles"]):
            axis.axvline(quantile, color="#777777", lw=.7, ls="--" if index == 1 else ":")
        observed = summary[f"observed_{zone}"]
        p = summary["center_p_negative" if column == 0 else "surround_p_positive"]
        axis.axvline(observed, color="#222222", lw=1.4)
        axis.set_title("Center null" if column == 0 else "Surround null", pad=25)
        precision = 4 if column == 0 else 6
        axis.text(0,1.02, f"observed = {observed:.{precision}f}   p = {p:.6f}",
                  transform=axis.transAxes, fontsize=7, va="bottom")
        axis.set(xlabel="Normalized zone covariance", ylabel="Null iterations")
        axis.xaxis.set_major_locator(MaxNLocator(4))
        axis.yaxis.set_major_locator(MaxNLocator(4, integer=True))
        if column == 0:
            inset = axis.inset_axes([.29,.21,.43,.37])
            inset.hist(values[:,0], bins=30, color="#a9c1d3", edgecolor="white", linewidth=.2)
            for index, quantile in enumerate(summary["center_null_quantiles"]):
                inset.axvline(quantile, color="#777777", lw=.6, ls="--" if index == 1 else ":")
            inset.spines[["top", "right"]].set_visible(False)
            inset.set_title("Null range (zoom)", fontsize=6.5, pad=3)
            inset.tick_params(labelsize=6, length=2)
            inset.xaxis.set_major_locator(MaxNLocator(3))
            inset.yaxis.set_major_locator(MaxNLocator(2, integer=True))
    handles = [Patch(facecolor="#a9c1d3", label="Null shifts"),
               Line2D([],[],color="#222222",lw=1.4,label="Observed"),
               Line2D([],[],color="#777777",ls=":",lw=.7,label="Null 2.5 / 97.5%"),
               Line2D([],[],color="#777777",ls="--",lw=.7,label="Null median")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.53,.01), ncol=4, frameon=False, columnspacing=1)
    save_figure(fig, folder, "figure_4_full_pipeline_null")


def support_figure(folder: Path, population: dict) -> None:
    """Supplementary [15,15] ROI/fly counts retain missing-support≠zero interpretation."""
    fig, axes = plt.subplots(1, 2, figsize=(WIDTH, 3.3), layout="constrained")
    for index, (axis, key, title) in enumerate(zip(axes, ("roi_support", "fly_support"), ("ROI support", "Fly support"), strict=True)):
        panel_axis(axis, chr(65+index), title)
        counts = population[key]
        shown = axis.imshow(counts, cmap="cividis", origin="lower", interpolation="nearest", vmin=0, vmax=float(counts.max()))
        axis.set_box_aspect(1)
        axis.set(xlabel="Column (pixel)", ylabel="Row (pixel)")
        axis.set_xticks([0,7,14])
        axis.set_yticks([0,7,14])
        colorbar = fig.colorbar(shown, ax=axis, shrink=.78, pad=.03)
        colorbar.set_label("Contributing ROIs" if index == 0 else "Contributing flies")
        maximum = int(counts.max())
        colorbar.set_ticks([0, maximum//2, maximum] if index == 0 else range(maximum+1))
    save_figure(fig, folder, "supplementary_s1_support")


def methods_figure(folder: Path) -> None:
    """Separate trimmed/subpixel spatial inference from full-record temporal diagnosis."""
    fig, axis = plt.subplots(figsize=(WIDTH, 5.5))
    fig.subplots_adjust(left=.015, right=.985, bottom=.025, top=.99)
    axis.set(xlim=(0,1), ylim=(0,1))
    axis.axis("off")
    nodes = [(.5,.94,.80,"Saved stimulus + TTL\nROI MeanN fluorescence"),
             (.5,.83,.58,"TTL alignment\nTechnical ROI quality control"),
             (.5,.72,.58,"Gaussian baseline: F − G10s(F)\nFull and 3σ-trimmed responses"),
             (.5,.61,.72,"40 × 15 × 15 history → reverse correlation\nCov(stimulus, R) → individual STRF z-score"),
             (.27,.49,.44,"Global RF-energy peak lag\nPrimary trimmed STRF at lag1"),
             (.75,.49,.43,"Frozen full-record diagnostic\n4 × 10 reference centers"),
             (.27,.37,.44,"Gaussian cross-section centers\nBilinear subpixel alignment"),
             (.75,.37,.43,"Integer no-wrap alignment\nNative lag0–39 temporal metrics"),
             (.27,.25,.44,"ROI → fly → equal-fly population\nSpatial center / surround metrics"),
             (.75,.25,.43,"lag4 peripheral candidate\nPost-hoc, not confirmatory"),
             (.27,.13,.44,"Full-pipeline circular-shift null\n500 shifts · minimum distance 60 s")]
    for x, y, width, text in nodes:
        axis.add_patch(FancyBboxPatch((x-width/2,y-.036),width,.072,
            boxstyle="round,pad=0.008,rounding_size=0.015", facecolor="white", edgecolor="#617f93", linewidth=.8))
        axis.text(x,y,text,ha="center",va="center",fontsize=8.3,linespacing=1.5)
    for start, end in [(0,1),(1,2),(2,3),(3,4),(3,5),(4,6),(5,7),(6,8),(7,9),(8,10)]:
        x1,y1,_,_ = nodes[start]
        x2,y2,_,_ = nodes[end]
        axis.annotate("", xy=(x2,y2+.045), xytext=(x1,y1-.045),
                      arrowprops={"arrowstyle":"->", "color":"#555555", "lw":.8, "shrinkA":0, "shrinkB":0})
    axis.text(.75,.11,"Temporal reference differs from\nprimary spatial estimator.",ha="center",va="center",fontsize=8,color="#555555")
    axis.text(.5,.025,"No wrap · missing support is NaN · biological n = 5",ha="center",fontsize=8,color="#444444")
    save_figure(fig, folder, "methods_pipeline")


def final_figures(folder: Path, flies: list, population: dict, temporal: list,
                  null_values: np.ndarray, null_summary: dict, config: dict) -> None:
    """Four main figures, support supplement and methods schematic from unchanged arrays."""
    folder.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(STYLE):
        receptive_field_figure(folder, flies, population)
        spatial_zone_figure(folder, flies, population, config)
        temporal_figure(folder, temporal)
        null_figure(folder, null_values, null_summary)
        support_figure(folder, population)
        methods_figure(folder)
