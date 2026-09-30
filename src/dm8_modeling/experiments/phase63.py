"""Independent fly RFs followed by full-pipeline exploratory shift validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from ..data import align_session, discover_sessions
from ..features.temporal_basis import binned_design
from ..io.stage_manifest import verify_stage_manifest, write_stage_manifest
from ..io.tables import save_csv, save_json
from ..preprocessing.rf_response import li_style_relative_response
from ..rf.characterization import fdr_q_values, reverse_correlation, rf_maps
from ..rf.population import image_correlation, pairwise_median, valid_mean, zone_means
from ..rf.validation import (align_temporal_bins, cancellation, consensus, empirical_test,
                             fly_mean_bins, radial_extremes, summarize_map, vector_correlation)
from .workflow import WorkflowContext


@dataclass
class PreparedFly:
    """One recording only: no fields are estimated from another fly."""
    aligned: object
    raw: np.ndarray
    technical_indices: np.ndarray
    eligible: np.ndarray
    design: np.ndarray


def prepare_fly(aligned, estimator: dict) -> PreparedFly:
    raw = aligned.response
    technical = (np.isfinite(raw).all(axis=0) &
                 (np.mean(raw == 0, axis=0) < estimator['max_raw_zero_fraction']) &
                 (np.std(np.where(np.isfinite(raw), raw, 0), axis=0) > estimator['minimum_response_std']))
    selected = np.flatnonzero(technical)
    if not len(selected):
        raise ValueError(f'No technically valid ROI: {aligned.session.fly}')
    history = estimator['temporal_bins'] * estimator['updates_per_bin']
    eligible = aligned.update_index >= history - 1
    design = binned_design(aligned.stimulus, aligned.update_index[eligible],
                           estimator['temporal_bins'], estimator['updates_per_bin'])
    return PreparedFly(aligned, raw[:, selected], selected, eligible, design)


def estimate_fly(prepared: PreparedFly, estimator: dict, shift: int = 0) -> dict:
    """Shift raw jointly across ROIs, then redo preprocessing, RF and center."""
    raw = np.roll(prepared.raw, shift, axis=0) if shift else prepared.raw
    li, _ = li_style_relative_response(raw, prepared.aligned.imaging_time_us,
                                       estimator['gaussian_sigma_seconds'], estimator['gaussian_truncate_sigma'])
    li = li[prepared.eligible]
    std = li.std(axis=0)
    valid = std > estimator['minimum_response_std']
    if not np.any(valid):
        raise ValueError('No usable response after Li-style transformation')
    scaled = ((li[:, valid] - li[:, valid].mean(axis=0)) / std[valid]).astype(np.float32)
    kernel = reverse_correlation(prepared.design, scaled)
    centers = rf_maps(kernel, estimator['temporal_bins'])['centers']
    kernel = kernel.reshape(estimator['temporal_bins'], 15, 15, -1)
    aligned_bins = align_temporal_bins(kernel, centers)
    included = np.isfinite(centers).all(axis=1)
    bins = fly_mean_bins(aligned_bins, included)
    return {'kernel': kernel, 'centers': centers, 'aligned_bins': aligned_bins,
            'mean_bins': bins, 'mean_map': bins.mean(axis=0), 'included': included,
            'scaled_response': scaled, 'selected_indices': prepared.technical_indices[valid]}


def draw_shifts(frame_count: int, interval_us: float, config: dict, rng) -> np.ndarray:
    """Sample only offsets whose circular distance is at least the fixed bound."""
    minimum = int(np.ceil(config['minimum_shift_seconds'] * 1_000_000 / interval_us))
    if frame_count <= 2 * minimum:
        raise ValueError('Recording too short for the prespecified null shift exclusion')
    return rng.integers(minimum, frame_count - minimum + 1, size=config['n_null'])


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_ready(value.tolist())
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    return value


def _observed_fly(prepared: PreparedFly, estimator: dict, config: dict, out: Path) -> dict:
    result = estimate_fly(prepared, estimator)
    response = result['scaled_response']
    midpoint = len(response) // 2
    first = rf_maps(reverse_correlation(prepared.design[:midpoint], response[:midpoint]), 4)['centers']
    second = rf_maps(reverse_correlation(prepared.design[midpoint:], response[midpoint:]), 4)['centers']
    distance = np.linalg.norm(first - second, axis=1)
    included = result['included']
    stable = included & np.isfinite(distance) & (distance <= estimator['center_uncertain_split_distance_px'])
    uncertain = included & ~stable
    groups = {'ALL': included, 'STABLE': stable, 'UNCERTAIN': uncertain}
    group_bins = np.stack([fly_mean_bins(result['aligned_bins'], mask) for mask in groups.values()])
    original = result['kernel'].mean(axis=0)
    original_mean = valid_mean(original[:, :, included], 2)[0]
    aligned_spatial = result['aligned_bins'].mean(axis=0)
    statistics = summarize_map(result['mean_map'], estimator)
    trajectory = np.array([zone_means(image, estimator['center_zone_radius_px'],
                                       estimator['surround_zone_inner_px'], estimator['surround_zone_outer_px'])
                           for image in result['mean_bins']])
    temporal_radial = np.stack([summarize_map(image, estimator)['radial_profile']
                               for image in result['mean_bins']])
    peaks = radial_extremes(statistics['radial_profile'], np.asarray(estimator['radial_edges_pixels']),
                            config['radial_peak_min_lower_edge_px'])
    summary = {'fly': prepared.aligned.session.fly, 'run_id': prepared.aligned.session.run_id,
               'total_roi': prepared.aligned.response.shape[1],
               'technical_roi': len(prepared.technical_indices), 'aligned_roi': int(included.sum()),
               'stable_roi': int(stable.sum()), 'uncertain_roi': int(uncertain.sum()),
               'stable_fraction': float(stable.sum() / included.sum()),
               'negative_center_roi_fraction': float(np.mean(aligned_spatial[7, 7, included] < 0)),
               'within_roi_r_before': pairwise_median(original[:, :, included]),
               'within_roi_r_after': pairwise_median(aligned_spatial[:, :, included]),
               'split_distance_quantiles_px': np.nanquantile(distance, [.25, .5, .75]),
               'center_zone': statistics['center_zone'], 'surround_zone': statistics['surround_zone'],
               'center_pixel': statistics['center_pixel'],
               'strongest_center_bin': int(np.argmax(np.abs(trajectory[:, 0])) + 1),
               'center_trajectory': trajectory[:, 0], 'surround_trajectory': trajectory[:, 1],
               'temporal_center_cancellation': cancellation(trajectory[:, 0]),
               'temporal_surround_cancellation': cancellation(trajectory[:, 1]),
               **peaks, 'source_hashes': prepared.aligned.qc['source_sha256']}
    np.savez_compressed(out / f'{summary["fly"]}_observed.npz',
                        kernel=result['kernel'], centers=result['centers'], aligned_bins=result['aligned_bins'],
                        valid_pixel_mask=np.isfinite(result['aligned_bins']), mean_bins=result['mean_bins'],
                        original_mean=original_mean, mean_map=result['mean_map'],
                        group_bins=group_bins, group_roi_counts=[mask.sum() for mask in groups.values()],
                        temporal_radial=temporal_radial, split_distance=distance,
                        included=included, stable=stable, uncertain=uncertain,
                        selected_roi_indices=result['selected_indices'],
                        roi_labels=np.array(prepared.aligned.roi_labels)[result['selected_indices']],
                        source_original_results_rows=prepared.aligned.original_sample_index[prepared.eligible])
    return {'summary': summary, 'bins': result['mean_bins'], 'map': result['mean_map'],
            'original': original_mean, 'groups': group_bins, 'statistics': statistics,
            'temporal_radial': temporal_radial}


def _null_fly(prepared: PreparedFly, estimator: dict, shifts: np.ndarray, out: Path) -> dict:
    count = len(shifts)
    maps = np.full((count, 15, 15), np.nan, dtype=np.float32)
    statistics = np.full((count, 4), np.nan)
    radial = np.full((count, len(estimator['radial_edges_pixels']) - 1), np.nan)
    roi_counts = np.zeros(count, dtype=int)
    center_change = np.zeros(count, dtype=int)
    observed_centers = estimate_fly(prepared, estimator)['centers']
    for iteration, shift in enumerate(shifts):
        result = estimate_fly(prepared, estimator, int(shift))
        maps[iteration] = result['mean_map']
        stats = summarize_map(result['mean_map'], estimator)
        statistics[iteration] = [stats[name] for name in
                                 ('center_zone', 'center_pixel', 'max_central_magnitude', 'surround_zone')]
        radial[iteration] = stats['radial_profile']
        roi_counts[iteration] = result['included'].sum()
        if result['centers'].shape == observed_centers.shape:
            center_change[iteration] = np.sum(np.any(result['centers'] != observed_centers, axis=1))
        else:
            center_change[iteration] = len(result['centers'])
        if (iteration + 1) % 250 == 0:
            print(f'{prepared.aligned.session.fly}: full-pipeline null {iteration + 1}/{count}', flush=True)
    np.savez_compressed(out / f'{prepared.aligned.session.fly}_null.npz',
                        shifts_frames=shifts, maps=maps, statistics=statistics, radial_profiles=radial,
                        valid_roi_counts=roi_counts, changed_center_counts=center_change)
    return {'maps': maps, 'statistics': statistics, 'radial': radial, 'roi_counts': roi_counts,
            'changed_center_counts': center_change, 'shifts': shifts}


def run_phase63(root: Path) -> Path:
    root = root.expanduser().resolve()
    context = WorkflowContext.load(root)
    config_path = root / 'configs/phase6_3_validation.json'
    config = json.loads(config_path.read_text())
    estimator_path = root / config['estimator_config']
    estimator = json.loads(estimator_path.read_text())
    baseline = context.output_root / 'phase_06/population_rf'
    verify_stage_manifest(baseline / 'stage_manifest.json', estimator)
    if config['schema_version'] != 'phase6_3_fly_population_validation_v1' or config['n_null'] < 500:
        raise ValueError('Phase 6.3 requires at least 500 frozen full-pipeline null iterations')
    if estimator['temporal_bins'] != 4 or estimator['updates_per_bin'] != 10:
        raise ValueError('Keep the Phase 6.2 temporal representation')
    sessions = discover_sessions(context.data_root)
    if len(sessions) != 5 or len({session.fly for session in sessions}) != 5:
        raise ValueError('Expected five distinct fly recordings')
    out = context.output_root / 'phase_06/fly_population_validation'
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config['random_seed'])
    observed, nulls = [], []
    for session in sessions:
        prepared = prepare_fly(align_session(session), estimator)
        item = _observed_fly(prepared, estimator, config, out)
        with np.load(baseline / f'{session.fly}_rf.npz') as saved:
            np.testing.assert_allclose(item['map'], saved['fly_mean'], rtol=2e-5, atol=2e-8)
        interval = float(np.median(np.diff(prepared.aligned.imaging_time_us)))
        shifts = draw_shifts(len(prepared.raw), interval, config, rng)
        null = _null_fly(prepared, estimator, shifts, out)
        observed.append(item)
        nulls.append(null)
        print(f'{session.fly}: independent analysis complete', flush=True)
    fly_maps = np.stack([item['map'] for item in observed])
    fly_bins = np.stack([item['bins'] for item in observed])
    group_bins = np.stack([item['groups'] for item in observed])  # fly, group, bin, row, col
    original_maps = np.stack([item['original'] for item in observed])
    population, fly_count = valid_mean(fly_maps, 0)
    population_bins = valid_mean(fly_bins, 0)[0]
    population_groups, group_fly_counts = valid_mean(group_bins, 0)
    lofo_bins = np.stack([valid_mean(np.delete(fly_bins, index, axis=0), 0)[0] for index in range(5)])
    null_maps = np.stack([item['maps'] for item in nulls], axis=1)  # iteration, fly, row, col
    null_population, null_fly_counts = valid_mean(null_maps, 1)
    null_population_stats = np.array([[summarize_map(image, estimator)[key] for key in
                                      ('center_zone', 'center_pixel', 'max_central_magnitude', 'surround_zone')]
                                     for image in null_population])
    null_population_radial = np.stack([summarize_map(image, estimator)['radial_profile']
                                      for image in null_population])
    null_fly_stats = np.stack([item['statistics'] for item in nulls], axis=1)
    null_negative_count = np.sum(null_fly_stats[:, :, 0] < 0, axis=1)
    cons = consensus(fly_maps)
    pairwise = np.array([[vector_correlation(a, b) for b in fly_maps] for a in fly_maps], dtype=float)
    fly_stats = [item['statistics'] for item in observed]
    population_stats = summarize_map(population, estimator)
    all_stats = fly_stats + [population_stats]
    all_null_stats = [item['statistics'] for item in nulls] + [null_population_stats]
    p_rows = []
    labels = [session.fly for session in sessions] + ['population']
    primary_p = []
    for label, stats, values in zip(labels, all_stats, all_null_stats):
        test = empirical_test(stats['center_zone'], values[:, 0])
        primary_p.append(test['p'])
        p_rows.append({'unit': label, 'observed_center_zone': stats['center_zone'],
                       'center_zone_p_negative': test['p'], 'center_zone_q_BH6': None,
                       'null_center_zone_low': test['null_quantiles'][0],
                       'null_center_zone_median': test['null_quantiles'][1],
                       'null_center_zone_high': test['null_quantiles'][2],
                       'center_pixel_p_negative': empirical_test(stats['center_pixel'], values[:, 1])['p'],
                       'max_central_p_magnitude': empirical_test(stats['max_central_magnitude'], values[:, 2], 'magnitude')['p'],
                       'n_valid_null': test['n_valid']})
    for row, q in zip(p_rows, fdr_q_values(np.asarray(primary_p, dtype=float))):
        row['center_zone_q_BH6'] = q
    comparisons = []
    for index, item in enumerate(observed):
        rest = lofo_bins[index].mean(axis=0)
        rest_stats = summarize_map(rest, estimator)
        comparisons.append({'fly': labels[index], 'r_vs_population': vector_correlation(item['map'], population),
                             'r_vs_other_four': vector_correlation(item['map'], rest),
                             'center_deviation': item['statistics']['center_zone'] - population_stats['center_zone'],
                             'surround_deviation': item['statistics']['surround_zone'] - population_stats['surround_zone'],
                             'radial_r_vs_population': vector_correlation(item['statistics']['radial_profile'], population_stats['radial_profile']),
                             'radial_r_vs_other_four': vector_correlation(item['statistics']['radial_profile'], rest_stats['radial_profile']),
                             'temporal_center_r_vs_population': vector_correlation(item['summary']['center_trajectory'],
                                  np.array([summarize_map(image, estimator)['center_zone'] for image in population_bins])),
                             'temporal_surround_r_vs_population': vector_correlation(item['summary']['surround_trajectory'],
                                  np.array([summarize_map(image, estimator)['surround_zone'] for image in population_bins]))})
    zone_rows, group_rows, radial_test_rows = [], [], []
    for group_index, group in enumerate(('ALL', 'STABLE', 'UNCERTAIN')):
        for index, label in enumerate(labels):
            bins = group_bins[index, group_index] if index < 5 else population_groups[group_index]
            stats = summarize_map(bins.mean(axis=0), estimator)
            group_rows.append({'unit': label, 'group': group, 'center_zone': stats['center_zone'],
                               'surround_zone': stats['surround_zone'], 'center_pixel': stats['center_pixel'],
                               'valid_flies': int(np.isfinite(bins[:, 7, 7]).all()) if index < 5 else
                                              int(np.min(group_fly_counts[group_index, :, 7, 7]))})
    for bin_index in range(5):  # 0: time-integrated; 1..4: original temporal bins
        maps = fly_maps if bin_index == 0 else fly_bins[:, bin_index - 1]
        values = np.array([[summarize_map(image, estimator)[zone] for zone in ('center_zone', 'surround_zone')]
                           for image in maps])
        for zone_index, zone in enumerate(('center', 'surround')):
            v = values[:, zone_index]
            zone_rows.append({'temporal_bin': bin_index, 'zone': zone,
                              **{f'fly{i+1}': v[i] for i in range(5)},
                              'mean': v.mean(), 'sd_between_flies': v.std(ddof=1),
                              'minimum': v.min(), 'maximum': v.max(), 'negative_flies': int((v < 0).sum()),
                              'positive_flies': int((v > 0).sum()),
                              'cross_fly_cancellation': float(cancellation(v))})
    for label, stats, null_radial in zip(labels, all_stats, [item['radial'] for item in nulls] + [null_population_radial]):
        for index, value in enumerate(stats['radial_profile']):
            neg = empirical_test(value, null_radial[:, index])
            pos = empirical_test(-value, -null_radial[:, index])
            two = min(1., 2 * min(neg['p'], pos['p'])) if neg['p'] is not None else None
            radial_test_rows.append({'unit': label, 'radial_bin': index, 'observed': value,
                                     'p_negative_unadjusted': neg['p'], 'p_two_tail_unadjusted': two,
                                     'null_low': neg['null_quantiles'][0], 'null_median': neg['null_quantiles'][1],
                                     'null_high': neg['null_quantiles'][2]})
    arrays_path = out / 'validation_arrays.npz'
    np.savez_compressed(arrays_path, fly_maps=fly_maps, fly_bins=fly_bins, original_maps=original_maps,
                        population=population, population_bins=population_bins,
                        group_bins=group_bins, population_groups=population_groups, group_fly_counts=group_fly_counts,
                        lofo_bins=lofo_bins, pairwise_correlations=pairwise,
                        null_population=null_population.astype(np.float32), null_population_statistics=null_population_stats,
                        null_population_radial=null_population_radial, null_fly_statistics=null_fly_stats,
                        null_negative_fly_count=null_negative_count, null_fly_counts=null_fly_counts,
                        **cons, fly_count=fly_count, spatial_cancellation=cancellation(fly_maps),
                        radial_edges=np.asarray(estimator['radial_edges_pixels']))
    summary = {'status': config['status'], 'baseline_commit': config['baseline_commit'], 'config': config,
               'estimator': estimator, 'biological_n': 5, 'observed_matches_phase62': True,
               'fly_results': [item['summary'] for item in observed], 'comparisons': comparisons,
               'population': population_stats, 'primary_null_tests': p_rows,
               'null_5_negative_count': int(np.sum(null_negative_count == 5)),
               'null_5_negative_frequency': float(np.mean(null_negative_count == 5)),
               'null_5_negative_p_plus_one': float((1 + np.sum(null_negative_count == 5)) / (config['n_null'] + 1)),
               'null_negative_count_histogram': np.bincount(null_negative_count, minlength=6),
               'null_population_min_fly_count': int(null_fly_counts.min()),
               'null_center_reestimated_changes': [int(item['changed_center_counts'].min()) for item in nulls],
               'null_unique_shifts_per_fly': [int(len(np.unique(item['shifts']))) for item in nulls],
               'null_roi_count_ranges': [[int(item['roi_counts'].min()), int(item['roi_counts'].max())] for item in nulls],
               'consensus_pixel_counts': {str(value): int(np.sum(cons['signed_majority'] == value))
                                          for value in (-5, -4, -3, 0, 3, 4, 5)},
               'zone_temporal_summary': zone_rows, 'center_groups': group_rows,
               'fly4_influence': {'with_center': population_stats['center_zone'],
                                  'without_center': summarize_map(lofo_bins[3].mean(axis=0), estimator)['center_zone'],
                                  'with_surround': population_stats['surround_zone'],
                                  'without_surround': summarize_map(lofo_bins[3].mean(axis=0), estimator)['surround_zone']}}
    summary_path = save_json(out / 'summary.json', _json_ready(summary))
    table_paths = [save_csv(out / name, _json_ready(rows)) for name, rows in (
        ('null_tests.csv', p_rows), ('fly_population_comparison.csv', comparisons),
        ('zone_temporal_summary.csv', zone_rows), ('center_stability_groups.csv', group_rows),
        ('radial_null_diagnostics.csv', radial_test_rows))]
    fly_rows = [{key: json.dumps(_json_ready(value)) if isinstance(value, (dict, list, np.ndarray)) else value
                 for key, value in item['summary'].items()} for item in observed]
    table_paths.append(save_csv(out / 'fly_independent_summary.csv', _json_ready(fly_rows)))
    save_csv(out / 'pairwise_fly_correlation.csv', [{'fly': labels[index],
             **{labels[j]: pairwise[index, j] for j in range(5)}} for index in range(5)])
    from .rf_validation_plots import make_figures
    figure_paths = make_figures(out, summary, estimator)
    verify_stage_manifest(baseline / 'stage_manifest.json', estimator)
    code_paths = [root / 'src/dm8_modeling/experiments/phase63.py',
                  root / 'src/dm8_modeling/experiments/rf_validation_plots.py',
                  root / 'src/dm8_modeling/rf/validation.py',
                  root / 'src/dm8_modeling/rf/characterization.py',
                  root / 'src/dm8_modeling/rf/population.py',
                  root / 'src/dm8_modeling/preprocessing/rf_response.py']
    sources = sorted(path for path in context.data_root.rglob('*') if path.is_file() and path.name != '.DS_Store')
    outputs = [arrays_path, summary_path, *table_paths, out / 'pairwise_fly_correlation.csv',
               *figure_paths, *sorted(out.glob('fly*_observed.npz')), *sorted(out.glob('fly*_null.npz'))]
    return write_stage_manifest('phase_06_3_fly_population_validation', out, config,
                                [config_path, estimator_path, *code_paths, *sources], outputs, root,
                                details={'null_iterations': config['n_null'], 'independent_fly_analysis': True,
                                         'observed_matches_phase62': True, 'biological_n': 5})
