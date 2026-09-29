# Dm8 experimental neural encoding

This repository starts a reproducible analysis of the five `UV-15Hz` fly runs
in `Dm8_module`. It reads the experiment directory without changing it. The
current scientific target is a **single-condition spatiotemporal encoding
baseline**. The recorded `Results.csv` columns are ROI mean intensities; their
Dm8 identity and calcium preprocessing have not yet been independently
verified.

Read the [first-phase results](docs/PHASE1_REPORT.md) before interpreting any
model output; the current held-out prediction is weak across all five runs.

## Modeling plan

1. Verify source files, their clocks, ROI tables, and stimulus arrays.
2. Align frozen 15 Hz stimulus updates to Zeiss imaging frames using the
   marker-locked DLP TTL and Zeiss TTL, both on the acquisition device's
   microsecond clock.
3. Fit a causal spatiotemporal white-noise STRF baseline. Test prediction on
   a later time block separated from training by a temporal gap. Compare the
   full STRF with its rank-one space/time approximation.
4. If source identity and signal processing are verified, compare a
   regularized interpretable model with a compact neural network under the
   same train/test split. Separately controlled time and wavelength data are
   required for independent temporal and spectral claims.
5. With matching multi-condition data, test dimension interactions and build
   the mathematical/mechanistic and data-driven integrated models.

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
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module --qc-only
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module \
  --response-transform causal_ema_60s --output-dir outputs/ema_exploratory
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module \
  --model ridge --output-dir outputs/ridge_raw
```

`--data-root` can point to `Dm8_module` or its `UV-15Hz` child. No absolute
source path is embedded in the software. The command reads every discovered
`fly*/<run>/Results.csv` session and writes results under
`outputs/first_pass/`, which Git ignores. Use `--output-dir` to choose another
result location. `--lag-count` changes the number of preceding 15 Hz stimulus
updates; the default 45 corresponds to approximately three seconds.
The optional 60-second exponential baseline subtraction uses only current
and past responses. It is an exploratory drift-control comparison, not ΔF/F.

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

## Outputs and interpretation

`data_qc.json` reports input counts, clock intervals, zero intensity rate,
and existing acquisition flags. `baseline_metrics.json` contains per-ROI and
session-level held-out correlations, R², and rank-one kernel energy fractions.
`baseline_kernels.npz` contains the full and rank-one STA kernels with shape
`lag × 15 × 15 × ROI`. `summary.json` collects the session-level values.
With `--model ridge`, `ridge_coefficients.npz` stores four temporally binned
spatial filters and `baseline_metrics.json` records validation penalty choice
and held-out scores.

This first pass uses raw ROI mean intensity as the target. It does **not**
label the target as ΔF/F, infer GCaMP or genotype, establish Dm8 cell identity,
or calibrate wavelength or irradiance. The `UV-15Hz` folder label is not a
physical spectral measurement. All five flies received the same frozen
stimulus sequence, so the within-run late-block test measures prediction on
a later portion of that sequence; it does not test a new random seed,
stimulus family, or
independent-fly generalization test. A dedicated analysis must quantify
repeat reliability and biological response quality before strong conclusions.

The existing `alife_study_exp` repository is an Allen Visual Coding practice
project; it does not contain this experiment's stimulus-generation code. The
frozen stimulus arrays in `Dm8_module` are sufficient for this first pass.
