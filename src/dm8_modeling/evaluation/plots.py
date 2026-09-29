"""Dependency-free SVG diagnostic figures for the five-fly dataset."""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np

from ..datasets.splits import SPLIT_NAMES


def _text(x, y, value, size=13, color="#213547"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-family="Arial,sans-serif">{escape(str(value))}</text>'


def _rect(x, y, width, height, fill, stroke="none"):
    return f'<rect x="{x}" y="{y}" width="{max(width, 0):.1f}" height="{height}" fill="{fill}" stroke="{stroke}"/>'


def _panel(parts, x, y, title, subtitle=""):
    parts.append(_rect(x, y, 460, 190, "#ffffff", "#d6dfe6"))
    parts.append(_text(x + 18, y + 25, title, 16))
    if subtitle:
        parts.append(_text(x + 18, y + 46, subtitle, 11, "#607080"))


def write_dataset_diagnostics(path: Path, individuals, processed, reliability, fold) -> Path:
    """Eight requested views: counts, scale, drift, reliability, two clocks, hierarchy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="970" height="850" viewBox="0 0 970 850">',
             _rect(0, 0, 970, 850, "#f3f6f9"), _text(22, 30, f"Dm8 integrated dataset | {fold.name}", 21)]
    positions = [(20 + (i % 2) * 480, 48 + (i // 2) * 198) for i in range(8)]
    for index, (x, y) in enumerate(positions):
        titles = ["1  Imaging observations", "2  ROI counts", "3  Response scale (train SD)",
                  "4  Raw drift (late minus early)", "5  Responsive ROI fraction",
                  "6  Shared temporal split", "7  One frozen stimulus", "8  Data hierarchy"]
        subtitles = ["Frames per fly; each ROI adds a response observation", "236 ROIs across 5 flies",
                     "Median within-fly raw intensity SD", "Median ROI raw intensity change, train first/last quarter",
                     "Membership from training only", "Same stimulus update boundaries for every fly",
                     "9,000 updates; five biological presentations", "Repeated y observations index one causal X table"]
        _panel(parts, x, y, titles[index], subtitles[index])
        if index in (0, 1, 2, 3, 4):
            raw_values = []
            for item in individuals:
                train = item.y_raw[item.split_label == 0]
                if index == 0:
                    value = len(item.y_raw) * len(item.roi_labels)
                elif index == 1:
                    value = len(item.roi_labels)
                elif index == 2:
                    value = float(np.median(processed[item.fly_id].scaler.scale))
                elif index == 3:
                    quarter = max(1, len(train) // 4)
                    value = float(np.median(train[-quarter:].mean(axis=0) - train[:quarter].mean(axis=0)))
                else:
                    value = float(np.mean(reliability[item.fly_id].selected))
                raw_values.append(value)
            biggest = max(max(abs(v) for v in raw_values), 1e-8)
            for row, (item, value) in enumerate(zip(individuals, raw_values, strict=True)):
                yy = y + 70 + row * 22
                parts.append(_text(x + 18, yy + 10, item.fly_id, 11))
                parts.append(_rect(x + 75, yy, abs(value) / biggest * 240, 13,
                                   "#377fb2" if value >= 0 else "#c46d4a"))
                parts.append(_text(x + 330, yy + 10, f"{value:,.2f}" if index in (2, 3, 4) else f"{value:,.0f}", 11))
        elif index == 5:
            bounds = fold.intervals()
            start = fold.history_updates - 1
            stop = max(fold.test_end_update, 9000)
            colors = {"train": "#377fb2", "validation": "#dfa43a", "test": "#5b9a65"}
            for name in ("train", "validation", "test"):
                a, b = bounds[name]
                parts.append(_rect(x + 20 + (a - start) / (stop - start) * 415, y + 80,
                                   (b - a) / (stop - start) * 415, 32, colors[name]))
            parts.append(_text(x + 20, y + 140, "blue train  |  amber validation  |  green test", 11))
            parts.append(_text(x + 20, y + 160, "white gaps purge overlapping causal histories", 11))
        elif index == 6:
            for row, item in enumerate(individuals):
                yy = y + 70 + row * 22
                parts.append(_text(x + 18, yy + 10, item.fly_id, 11))
                parts.append(_rect(x + 75, yy, 310, 12, "#a0c4df"))
            parts.append(_text(x + 18, y + 181, "Same digital update array verified byte-for-byte", 11))
        else:
            for row, label in enumerate(("1 frozen stimulus [8961,900]",
                                         "  5 flies / 5 recording runs",
                                         "    236 distinct ROI labels",
                                         "      1,907,824 indexed frame x ROI observations")):
                parts.append(_text(x + 20, y + 75 + row * 25, label, 13))
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n")
    return path


def write_model_comparison(path: Path, fold_name: str, models: dict) -> Path:
    """Show each model's all-ROI test R2 without hiding negative values."""
    rows = [(name, result["all_roi_median_r2"]) for name, result in models.items()
            if isinstance(result, dict) and result.get("all_roi_median_r2") is not None]
    height = 100 + len(rows) * 42
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}">',
             _rect(0, 0, 900, height, "#ffffff"), _text(20, 30, f"Held-out ROI prediction | {fold_name}", 20),
             _text(20, 50, "Median R2 across 236 ROIs; zero is prediction at test-set mean", 12, "#607080")]
    minimum = min([value for _, value in rows] + [-0.3])
    maximum = max([value for _, value in rows] + [0.1])
    low = min(-0.6, minimum * 1.2)
    high = max(0.2, maximum * 1.2)
    scale = 470 / (high - low)
    zero = 370 + (-low) * scale
    parts.append(_rect(zero, 64, 1, height - 75, "#4d5b67"))
    for row, (name, value) in enumerate(rows):
        yy = 80 + row * 42
        left = 370 + (min(value, 0) - low) * scale
        width = abs(value) * scale
        parts.append(_text(20, yy + 12, name, 12))
        parts.append(_rect(left, yy, width, 19, "#b86b4d" if value < 0 else "#4d9774"))
        parts.append(_text(795, yy + 14, f"{value:+.3f}", 12))
    parts.append('</svg>')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n")
    return path


def write_fly_scores(path: Path, model_name: str, summary: dict) -> Path:
    """Compact per-fly diagnostic in each model artifact directory."""
    flies = list(summary["per_fly"].items())
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="350" viewBox="0 0 780 350">',
             _rect(0, 0, 780, 350, "#ffffff"), _text(20, 28, model_name, 18),
             _text(20, 48, "Per-fly median held-out ROI R2; zero line at x=590", 12, "#607080"),
             _rect(590, 68, 1, 250, "#506070")]
    for index, (fly, values) in enumerate(flies):
        value = values["median_r2"]
        yy = 80 + index * 48
        parts.append(_text(20, yy + 17, f"{fly} ({values['roi_count']} ROIs)", 13))
        if value is not None:
            width = min(abs(value) * 600, 390)
            parts.append(_rect(590 - width if value < 0 else 590, yy, width, 22,
                               "#b86b4d" if value < 0 else "#4d9774"))
            parts.append(_text(630, yy + 17, f"{value:+.3f}", 13))
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n")
    return path


def write_population_scores(path: Path, rows: list[dict]) -> Path:
    """Five-fly summary for the distinct population-average target."""
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="780" height="350" viewBox="0 0 780 350">',
             _rect(0, 0, 780, 350, "#ffffff"), _text(20, 28, "Population-average target", 18),
             _text(20, 48, "Per-fly held-out R2; target is mean of selected ROI z-scores", 12, "#607080"),
             _rect(590, 68, 1, 250, "#506070")]
    for index, row in enumerate(rows):
        yy = 80 + index * 48
        value = row["r2"]
        parts.append(_text(20, yy + 17, f"{row['fly_id']} ({row['member_count']} members)", 13))
        if value is not None:
            width = min(abs(value) * 600, 390)
            parts.append(_rect(590 - width if value < 0 else 590, yy, width, 22,
                               "#b86b4d" if value < 0 else "#4d9774"))
            parts.append(_text(630, yy + 17, f"{value:+.3f}", 13))
    parts.append('</svg>')
    path.write_text("\n".join(parts) + "\n")
    return path
