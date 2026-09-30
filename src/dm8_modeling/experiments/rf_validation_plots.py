"""Fixed Phase 6.3 figures, all comparisons preserve sign and common units."""

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
import numpy as np

from ..rf.population import radial_profile, valid_mean, zone_means


def _map(axis, image, title, bound):
    artist = axis.imshow(image, origin='lower', cmap='coolwarm', vmin=-bound, vmax=bound)
    axis.set(title=title, xlabel='grid column (px)', ylabel='grid row (px)')
    return artist


def _finish(fig, path):
    fig.savefig(path, dpi=170, bbox_inches='tight')
    plt.close(fig)
    return path


def _curves(axis, radius, profiles, labels, title):
    for profile, label in zip(profiles, labels):
        axis.plot(radius, profile, marker='o', markersize=3,
                  color='black' if label == 'population' else None,
                  linewidth=2.5 if label == 'population' else 1.3, label=label)
    axis.axhline(0, color='gray', linewidth=.8)
    axis.set(title=title, xlabel='radius (grid px)', ylabel='signed covariance')
    axis.legend(fontsize=8)


def _trajectories(axis, bins, estimator, zone, labels, title):
    for images, label in zip(bins, labels):
        values = [zone_means(image, estimator['center_zone_radius_px'],
                             estimator['surround_zone_inner_px'], estimator['surround_zone_outer_px'])[zone]
                  for image in images]
        axis.plot(range(1, 5), values, 'o-', label=label,
                  color='black' if label in ('population', 'all 5 flies') else None,
                  linewidth=2.5 if label in ('population', 'all 5 flies') else 1.3)
    axis.axhline(0, color='gray', linewidth=.8)
    axis.set(title=title, xlabel='temporal bin (1 = most recent stimulus)', ylabel='signed covariance', xticks=range(1, 5))
    axis.legend(fontsize=8)


def make_figures(out: Path, summary: dict, estimator: dict) -> list[Path]:
    with np.load(out / 'validation_arrays.npz') as saved:
        data = {key: saved[key] for key in saved.files}
    maps, bins, population = data['fly_maps'], data['fly_bins'], data['population']
    labels = [item['fly'] for item in summary['fly_results']]
    all_labels = labels + ['population']
    edges = data['radial_edges']
    radius = (edges[:-1] + edges[1:]) / 2
    all_maps = np.concatenate((maps, population[None]), axis=0)
    all_bins = np.concatenate((bins, data['population_bins'][None]), axis=0)
    profiles = [radial_profile(image, edges)[0] for image in all_maps]
    map_bound = float(np.nanmax(np.abs(all_maps)))
    bin_bound = float(np.nanmax(np.abs(all_bins)))
    paths = []

    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
    for axis, image, label in zip(axes.flat, all_maps, all_labels):
        im = _map(axis, image, label, map_bound)
    fig.colorbar(im, ax=axes, shrink=.7, label='signed covariance')
    fig.suptitle('Independent fly RFs, then equal-fly population; n = 5 flies')
    paths.append(_finish(fig, out / 'figure_1_independent_rf.png'))

    fig, axis = plt.subplots(figsize=(8, 5), layout='constrained')
    _curves(axis, radius, profiles, all_labels, 'Signed radial RF: five flies and population')
    paths.append(_finish(fig, out / 'figure_2_radial.png'))

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout='constrained')
    im = axes[0].imshow(data['pairwise_correlations'], cmap='coolwarm', vmin=-1, vmax=1)
    axes[0].set(xticks=range(5), yticks=range(5), xticklabels=labels, yticklabels=labels, title='Pairwise fly-map Pearson r')
    for i in range(5):
        for j in range(5):
            axes[0].text(j, i, f'{data["pairwise_correlations"][i,j]:.2f}', ha='center', va='center')
    fig.colorbar(im, ax=axes[0], shrink=.8)
    for axis, prefix, title in ((axes[1], 'r_', 'Spatial similarity'), (axes[2], 'radial_r_', 'Radial similarity')):
        x = np.arange(5)
        axis.bar(x - .18, [item[f'{prefix}vs_population'] for item in summary['comparisons']], .36, label='vs population (shared data)')
        axis.bar(x + .18, [item[f'{prefix}vs_other_four'] for item in summary['comparisons']], .36, label='vs other four flies')
        axis.axhline(0, color='gray', linewidth=.8)
        axis.set(xticks=x, xticklabels=labels, ylim=(-1, 1), title=title, ylabel='Pearson r')
        axis.legend(fontsize=7)
    paths.append(_finish(fig, out / 'figure_3_similarity.png'))

    fig, axes = plt.subplots(1, 4, figsize=(16, 4.3), layout='constrained')
    im = _map(axes[0], population, 'Population mean', map_bound)
    fig.colorbar(im, ax=axes[0], shrink=.7)
    im = axes[1].imshow(np.std(maps, axis=0, ddof=1), origin='lower', cmap='viridis')
    axes[1].set_title('Between-fly SD')
    fig.colorbar(im, ax=axes[1], shrink=.7)
    cmap = ListedColormap(['#08306b','#2171b5','#9ecae1','#eeeeee','#fcbba1','#ef3b2c','#99000d'])
    codes = data['signed_majority']
    index = np.zeros_like(codes, dtype=int) + 3
    for i, value in enumerate((-5, -4, -3, 0, 3, 4, 5)):
        index[codes == value] = i
    im = axes[2].imshow(index, origin='lower', cmap=cmap, norm=BoundaryNorm(np.arange(-.5, 7.5), 7))
    axes[2].set_title('Exact sign majority; not significance')
    cb = fig.colorbar(im, ax=axes[2], ticks=range(7), shrink=.8)
    cb.ax.set_yticklabels(['5 neg','4 neg','3 neg','tie/missing','3 pos','4 pos','5 pos'])
    im = axes[3].imshow(data['spatial_cancellation'], origin='lower', cmap='magma', vmin=0, vmax=1)
    axes[3].set_title('Sign cancellation across flies')
    fig.colorbar(im, ax=axes[3], shrink=.8, label='0 none; 1 full cancellation')
    paths.append(_finish(fig, out / 'figure_4_consensus.png'))

    fig, axes = plt.subplots(5, 4, figsize=(13, 14), layout='constrained')
    for i in range(5):
        for j in range(4):
            im = _map(axes[i, j], bins[i, j], f'{labels[i]} / bin {j+1}', bin_bound)
    fig.colorbar(im, ax=axes, shrink=.45, label='signed covariance; common color scale')
    fig.suptitle('Each fly: four temporal bins using one full-RF center per ROI')
    paths.append(_finish(fig, out / 'figure_5_temporal_bins.png'))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    _trajectories(axes[0], all_bins, estimator, 0, all_labels, 'Center zone across temporal bins')
    _trajectories(axes[1], all_bins, estimator, 1, all_labels, 'Surround zone across temporal bins')
    paths.append(_finish(fig, out / 'figure_6_trajectories.png'))

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout='constrained')
    for axis, column, observed, title in (
        (axes[0], 0, summary['population']['center_zone'], 'Population center-zone mean'),
        (axes[1], 1, summary['population']['center_pixel'], 'Population center pixel')):
        axis.hist(data['null_population_statistics'][:, column], bins=35, color='#7896ad', label='1000 full-pipeline nulls')
        axis.axvline(observed, color='#c63737', linewidth=2, label=f'observed {observed:.5f}')
        axis.set(title=title, xlabel='signed covariance', ylabel='null count')
        axis.legend(fontsize=8)
    counts = np.bincount(data['null_negative_fly_count'], minlength=6)
    axes[2].bar(range(6), counts, color='#7896ad')
    axes[2].axvline(5, color='#c63737', linewidth=2, label='observed 5/5')
    axes[2].set(title=f'Null 5/5 negative: {counts[5]}/1000', xlabel='negative-center fly count', ylabel='null count', xticks=range(6))
    axes[2].legend(fontsize=8)
    fig.suptitle('EXPLORATORY INTERNAL VALIDATION; centers re-estimated on every null')
    paths.append(_finish(fig, out / 'figure_7_population_null.png'))

    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
    for i, axis in enumerate(axes.flat):
        if i == 5:
            axis.axis('off')
            continue
        test = summary['primary_null_tests'][i]
        axis.hist(data['null_fly_statistics'][:, i, 0], bins=35, color='#7896ad')
        axis.axvline(test['observed_center_zone'], color='#c63737', linewidth=2)
        axis.set(title=f'{labels[i]} / negative-tail p={test["center_zone_p_negative"]:.4f}', xlabel='center-zone signed covariance', ylabel='null count')
    fig.suptitle('Fly-specific full-pipeline null; exploratory, not independent replication')
    paths.append(_finish(fig, out / 'figure_8_fly_null.png'))

    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
    group_maps = data['population_groups'].mean(axis=1)
    bound = float(np.nanmax(np.abs(group_maps)))
    group_curve_values = []
    for i, group in enumerate(('ALL', 'STABLE', 'UNCERTAIN')):
        im = _map(axes[0, i], group_maps[i], f'{group}: five-fly mean', bound)
        group_fly_maps = data['group_bins'][:, i].mean(axis=1)
        group_profiles = [radial_profile(image, edges)[0] for image in group_fly_maps]
        group_profiles.append(radial_profile(group_maps[i], edges)[0])
        group_curve_values.extend(group_profiles)
        _curves(axes[1, i], radius, group_profiles, all_labels, f'{group}: radial curves')
    low, high = np.nanmin(group_curve_values), np.nanmax(group_curve_values)
    margin = .05 * (high - low)
    for axis in axes[1]:
        axis.set_ylim(low - margin, high + margin)
    fig.colorbar(im, ax=axes[0], shrink=.7)
    paths.append(_finish(fig, out / 'figure_9_center_groups.png'))

    fig, axes = plt.subplots(2, 4, figsize=(13, 7), layout='constrained')
    for i, (images, label) in enumerate(((data['population_bins'], 'all 5 flies'), (data['lofo_bins'][3], 'without fly4'))):
        for j in range(4):
            im = _map(axes[i, j], images[j], f'{label} / bin {j+1}', bin_bound)
    fig.colorbar(im, ax=axes, shrink=.7)
    paths.append(_finish(fig, out / 'supplement_fly4_influence.png'))

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    trajectories = np.concatenate((data['population_bins'][None], data['lofo_bins']))
    lofo_labels = ['all 5 flies'] + [f'without {label}' for label in labels]
    for zone, axis in enumerate(axes):
        _trajectories(axis, trajectories, estimator, zone, lofo_labels, ['LOFO center trajectory', 'LOFO surround trajectory'][zone])
    paths.append(_finish(fig, out / 'supplement_lofo_temporal.png'))

    fig, axes = plt.subplots(2, 3, figsize=(12, 8), layout='constrained')
    original = np.concatenate((data['original_maps'], valid_mean(data['original_maps'], 0)[0][None]))
    for axis, image, label in zip(axes.flat, original, all_labels):
        im = _map(axis, image, f'{label} original coordinates', map_bound)
    fig.colorbar(im, ax=axes, shrink=.7)
    paths.append(_finish(fig, out / 'supplement_unaligned.png'))

    for i, label in enumerate(labels):
        fig, axes = plt.subplots(2, 4, figsize=(14, 7), layout='constrained')
        _map(axes[0, 0], maps[i], 'Aligned mean RF', bin_bound)
        _map(axes[0, 1], data['original_maps'][i], 'Original mean RF', bin_bound)
        _curves(axes[0, 2], radius, [profiles[i]], [label], 'Integrated radial profile')
        bin_profiles = [radial_profile(image, edges)[0] for image in bins[i]]
        _curves(axes[0, 3], radius, bin_profiles, [f'bin{j+1}' for j in range(4)], 'Four temporal radial profiles')
        for j in range(4):
            im = _map(axes[1, j], bins[i, j], f'bin {j+1}', bin_bound)
        fig.colorbar(im, ax=[axes[0, 0], axes[0, 1], *axes[1]], shrink=.7)
        fig.suptitle(f'{label}: independent full-recording analysis')
        paths.append(_finish(fig, out / f'{label}_independent.png'))
    return paths
