# Dm8 modeling project

- Keep `simulate/` and `Dm8_module/` strictly read-only in this local workspace; exclude them from Git. Never move, rename or edit their contents.
- Preserve the distinction between ROI mean intensity and verified Dm8 calcium response.
- The active pipeline is descriptive RF characterization with offline Gaussian preprocessing. Any future predictive extension must fit and evaluate on separate time blocks and never use future stimulus frames to predict a response.
- Record data exclusions, timing assumptions and model settings with every result; retain source hashes and frozen numerical regression checks.
- Do not describe the `UV-15Hz` folder label as a measured wavelength or irradiance.
- Work on a task branch, run tests, and commit scoped changes.
- Keep one official runner (`analysis/run_final_analysis.py`) and one config (`configs/final_analysis.json`); historical experiments belong in Git history.
