# Dm8 experimental neural encoding

This repository starts a reproducible analysis of the five `UV-15Hz` fly runs
in `Dm8_module`. It reads the experiment directory without changing it. The
current graduation-design target is a **usable, explainable single-condition
stimulus-to-Dm8-response model**. By project convention, these are Dm8 data.
The recorded `Results.csv` columns are ROI mean intensities, so the numerical
target is this measured signal rather than a derived ΔF/F trace.

Start with the [workspace overview](docs/WORKSPACE_OVERVIEW.md) to see how
`simulate/`, `Dm8_module/`, and the analysis code connect, then the
[Phase 5 final predictive report](docs/FINAL_PREDICTIVE_MODEL_REPORT.md).
The earlier [single-fly report](docs/DM8_MODELING_FINAL_REPORT.md) is retained as historical context.
Its evidence is detailed in the [first-phase results](docs/PHASE1_REPORT.md),
[validated pixel-model report](docs/PHASE2_REPORT.md), and
[stimulus provenance and control report](docs/PHASE3_REPORT.md), plus the
[compact CNN comparison](docs/PHASE4_CNN_COMPARISON.md), before
interpreting model output. The [graduation-design guide](docs/GRADUATION_DESIGN_GUIDE.md)
gives the final presentation path. Most ROIs remain weakly predicted, while
a subset has a reproducible local stimulus response.

## Modeling plan

1. Verify source files, their clocks, ROI tables, and stimulus arrays.
2. Align frozen 15 Hz stimulus updates to Zeiss imaging frames using the
   marker-locked DLP TTL and Zeiss TTL, both on the acquisition device's
   microsecond clock.
3. Fit a causal spatiotemporal white-noise STRF baseline. Test prediction on
   a later time block separated from training by a temporal gap. Compare the
   full STRF with its rank-one space/time approximation.
4. Complete a compact, interpretable model and an independently executable
   prediction demo using the available Dm8 records. Explain both successful
   example ROIs and weak results across the full dataset.
5. Compare five-fly shared, hierarchical, low-rank and population models on
   synchronized stimulus folds. Spectral, genotype, and multi-condition
   models remain outside this graduation-design deliverable.

The follow-up compact CNN uses the same blocked evaluation as the pixel model.
It did not improve the overall held-out results; the pixel model remains the
primary explanation and the CNN is a saved, reproducible comparison.

The first interpretable predictive model is now a train-selected single-pixel
temporal filter. It provides an auditable local response estimate for the
current raw ROI target. It makes no spectral or genotype claim.

Phase 5 integrates five flies as biological repeats of **one** saved frozen
stimulus. The integrated data has 1,907,824 ROI-frame observations, 236 ROIs,
and 8,961 eligible stimulus-update positions. Shared STRF, hierarchical and
low-rank models did not consistently improve on independent models. The
[integrated dataset](docs/INTEGRATED_DATASET.md) and
[population-model guide](docs/POPULATION_MODELING.md) explain the exact
representations, model assumptions and limits.

Reverse correlation is a starting estimator, not the final mathematical
model. The rank-one kernel energy fraction describes an estimated kernel; it
does not by itself prove biological space/time separability. Held-out
prediction and reliability checks are needed.

## Setup and run

Use Python 3.11 or newer. On macOS:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/dm8-model dataset build-individual --workspace-root .
.venv/bin/dm8-model dataset build-integrated --workspace-root .
.venv/bin/dm8-model dataset describe-integrated --workspace-root .
.venv/bin/dm8-model fit all --workspace-root .
.venv/bin/dm8-model evaluate --workspace-root .
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling --inventory
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling --audit
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling --explain-session fly1
.venv/bin/python scripts/verify_stimulus_provenance.py \
  --data-root Dm8_module --stimulus-code-root simulate --output-dir outputs/audit
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling --qc-only
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling \
  --response-transform causal_ema_60s --output-dir outputs/ema_exploratory
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling \
  --model ridge --output-dir outputs/ridge_raw
.venv/bin/dm8-model --workspace-root /Users/irin/Documents/dm8_modeling \
  --model pixel --output-dir outputs/pixel_raw
.venv/bin/python scripts/validate_pixel_model.py --results-dir outputs/pixel_raw
.venv/bin/python scripts/check_common_mode.py \
  --data-root Dm8_module --results-dir outputs/pixel_raw
.venv/bin/dm8-predict --data-root Dm8_module \
  --model-file outputs/pixel_raw/fly1/20260619_105040/pixel_model.npz \
  --roi Mean29 --output-csv outputs/demo_fly1_Mean29.csv
.venv/bin/python -m pip install -e '.[deep]'
.venv/bin/dm8-cnn --data-root Dm8_module \
  --baseline-dir outputs/pixel_raw --output-dir outputs/cnn_comparison
.venv/bin/dm8-cnn-predict --data-root Dm8_module \
  --model-file outputs/cnn_comparison/fly1/20260619_105040/cnn_model.pt \
  --roi Mean29 --output-csv outputs/cnn_comparison/fly1_Mean29_replay.csv
```

`--workspace-root` points to the containing folder; `--data-root` and
`--stimulus-code-root` can override the two read-only sources. `--data-root`
can point to `Dm8_module` or its `UV-15Hz` child. No absolute
source path is embedded in the software. The command reads every discovered
`fly*/<run>/Results.csv` session and writes results under
`outputs/first_pass/`, which Git ignores. Use `--output-dir` to choose another
result location. `--lag-count` changes the number of preceding 15 Hz stimulus
updates; the default is 45 for STA and 18 for the pixel model, corresponding
to approximately three and 1.2 seconds, respectively. The ridge baseline
uses its own fixed bin design.
The optional 60-second exponential baseline subtraction uses only current
and past responses. It is an exploratory drift-control comparison, not ΔF/F.
Phase 5 uses `configs/phase5_first_round.json` and writes to Git-ignored
`outputs/experiments/phase5_first_round/`, including provenance manifests,
per-ROI metrics, fitted parameters, experiment registry and SVG diagnostics.
Its full matrix can be run without PyTorch. The Phase 5 folds are exploratory
because older phases already examined late-block results and the two folds
overlap in their roles.

## Inputs and meanings

| Source | Role |
|---|---|
| `stimulus_package/stim_realized.npz` | Frozen 15×15 binary stimulus updates, stored as −1/+1 for reverse correlation |
| `stimulus_package/stim_structure_priors.json` | Payload boundary, used only to exclude post-stimulus frames |
| `analysis_marker_lock/dlp_ttl_marker_locked.csv` | Recorded DLP frame clock after marker lock |
| `zeiss_ttl_<run>.csv` | Recorded microscope frame-out clock |
| `Results.csv` | Unprocessed mean ROI image intensity, one row per Zeiss frame |
| `task3_live_qc_summary.json` and marker-lock summary | Acquisition and timing quality flags |

The first column of `Results.csv` must be consecutive one-based frame
numbers, and its row count must equal the Zeiss TTL count. The number of
marker-locked DLP TTL records must equal the number of frozen display frames.
The pipeline fails loudly when these assumptions do not hold. It associates
each imaging frame with the most recent stimulus update on the recorded
acquisition clock, uses only preceding updates, and excludes frames outside
the stimulus payload. Zeiss frame-out TTL is used as an imaging timestamp
proxy because the precise within-frame exposure timing was not supplied.
For these binary runs, the loader independently reconstructs each frozen
stimulus from its saved seed, checks every update's 0/100 commanded gray
value against the display frames, and records the saved fly-side orientation
calibration. These checks validate the digital command, not optical
wavelength or irradiance at the fly.

## Outputs and interpretation

`data_qc.json` reports input counts, clock intervals, zero intensity rate,
and existing acquisition flags. `baseline_metrics.json` contains per-ROI and
session-level held-out correlations, R², and rank-one kernel energy fractions.
`baseline_kernels.npz` contains the full and rank-one STA kernels with shape
`lag × 15 × 15 × ROI`. `summary.json` collects the session-level values.
With `--model ridge`, `ridge_coefficients.npz` stores four temporally binned
spatial filters and `baseline_metrics.json` records validation penalty choice
and held-out scores.
With `--model pixel`, `pixel_metrics.json` records each ROI's training-selected
pixel, validation choice, test R²/correlation, and a circular-shift control.
The family-wide false-discovery adjustment covers all 236 ROIs across the
five runs. `pixel_model.npz` contains fitted coefficients, test predictions,
intercepts, selected pixels, test targets and timestamps. `dm8-predict`
reconstructs the held-out prediction from those fitted parameters and the
frozen stimulus, and checks it against the saved result. The validation script adds `validation.json` and
an SVG example figure under the chosen output directory. Its paired
moving-block bootstrap uses 68-frame blocks and a fixed random seed.
`scripts/check_common_mode.py` adds an exploratory same-time peer-ROI control
at `common_mode_control.json`. Because it uses other ROIs' test responses,
that control is not a stimulus-only predictive model.
The optional CNN comparison writes per-ROI paired test scores to
`outputs/cnn_comparison/fly*/<run>/cnn_metrics.json`, weights to `cnn_model.pt`,
and paired predictions to `cnn_test_predictions.npz`. `dm8-cnn-predict` replays
one ROI from the stimulus and saved CNN weights. PyTorch is only required for
these deep-model commands.

This graduation-design model treats the supplied runs as Dm8 data and uses
raw ROI mean intensity as the target. It does **not** call that target ΔF/F,
or calibrate wavelength or irradiance. The `UV-15Hz` folder label is not a
physical spectral measurement. All five flies received the same frozen
stimulus sequence, so the within-run late-block test measures prediction on
a later portion of that sequence; it does not test a new random seed,
stimulus family, or independent-fly generalization test. The project reports
these limits without requiring additional data for the graduation deliverable.

The experiment-engineering copy is `simulate/07E_260530_01/`. Its exact June
Windows revision is unavailable, but all eight frozen arrays in every run
reconstruct from the local 05E generator and each saved recipe. The frozen
arrays in `Dm8_module` remain the model input. See the [stimulus code audit](docs/STIMULUS_CODE_AUDIT.md),
[provenance map](docs/STIMULUS_PROVENANCE.md), [pipeline walkthrough](docs/DATA_PIPELINE_WALKTHROUGH.md),
[full data audit](docs/DATA_AUDIT_REPORT.md), and [baseline regression](docs/BASELINE_REGRESSION.md).
